# DTD Master Architecture, Product Vision & Monetization Matrix

**Status:** Locked Canonical Blueprint  
**Date:** 2026-08-29 (Updated: 2026-09-01)  
**Location Scope:** Greater Melbourne, Victoria, Australia  
**Repository Path:** `docs/strategy/DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md`

---

## Table of Contents
1. [Core Product Vision & Strategic Shift](#1-core-product-vision--strategic-shift)
2. [The 4-Step Supply-Led Flywheel](#2-the-4-step-supply-led-flywheel)
3. [UI/UX Audit & Modern Friction-Free Interaction Architecture](#3-uiux-audit--modern-friction-free-interaction-architecture)
4. [Modern OpenAI-Inspired Modular Education Architecture](#4-modern-openai-inspired-modular-education-architecture)
5. [Monetization Architecture & All-Inclusive Pricing Matrix](#5-monetization-architecture--all-inclusive-pricing-matrix)
6. [Refund Policy & Consumer Protections (ACL Compliance)](#6-refund-policy--consumer-protections-acl-compliance)
7. [Catchment, Geography & Inventory Model](#7-catchment-geography--inventory-model)
8. [Multi-Surface Ranking Algorithms](#8-multi-surface-ranking-algorithms)
9. [Fairness & Anti-Monopoly Governance](#9-fairness--anti-monopoly-governance)
10. [Pre-Implementation Gap Resolutions & Edge-Case Protocols](#10-pre-implementation-gap-resolutions--edge-case-protocols)
11. [Automated Communication Triggers Matrix](#11-automated-communication-triggers-matrix)
12. [Platform Integrations, Hardening Contracts & Complete Cost Matrix](#12-platform-integrations-hardening-contracts--complete-cost-matrix)
13. [Competitive Landscape & Startup Capital / Cloud Credit Strategy](#13-competitive-landscape--startup-capital--cloud-credit-strategy)
14. [Autonomous Post-Launch Engine & Operator Role in `/ops`](#14-autonomous-post-launch-engine--operator-role-in-ops)
15. [Prioritized Implementation Roadmap](#15-prioritized-implementation-roadmap)

---

## 1. Core Product Vision & Strategic Shift

### 1.1 The Underlying Vision
Dog Trainers Directory (DTD) is an authoritative, high-utility platform designed to solve the two biggest problems in the dog training market:
1. **For Dog Owners:** Finding a credible, vetted, and method-transparent local trainer without wading through noisy social media or generic listing walls.
2. **For Dog Trainers:** Gaining a dedicated, high-converting digital storefront—especially for independent/solo trainers without their own website—and receiving qualified, high-intent client inquiries without paying predatory commissions or burning money on dead leads.

### 1.2 The Strategic Posture Shift
* **Diagnosis of Past Stagnation:** Development over-indexed on defensive governance files, prelaunch locks (`PUBLIC_MATCHING_ENABLED=false`), and incremental "safest minimal change" patches (Codex loops), building complex operational oversight before establishing core product value.
* **Locked Operating Rule:** From this point forward, improvements are evaluated against **overall product vision and launch readiness**, not minimal-diff constraints. Code and user value represent truth.

---

## 2. The 4-Step Supply-Led Flywheel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Governed Lawful Ingestion                                                │
│    Accepted website/ABR launch evidence plus a separately licensed business │
│    discovery feed generate and maintain attributable supply.                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Rich Dedicated Business Profiles                                         │
│    Every trainer gets a polished, standalone, SEO-indexed page with         │
│    methods, specialties, suburbs serviced, pricing guide, and review data.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. High-Utility Discovery & Diagnostic Matching                             │
│    Open directory across ~300 Melbourne suburbs paired with a guided        │
│    diagnostic wizard that diagnoses dog issues and recommends top fits.     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. \"Claim & Enrich\" Monetization Engine                                     │
│    Trainers discover their active profile, claim it via automated OTP, and  │
│    upgrade to Pro / Suburb Sponsorship to unlock turnkey business tools.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 The Greater Melbourne Supply Seeding Blueprint & Data Schema

The complete source, processing, publication, and post-launch maintenance
contract is `docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`.

The current launch baseline is the accepted 20-profile batch built from
owner-approved official trainer websites plus active ABR evidence. Post-launch
expansion prefers a licensed Sensis/Thryv business-search API, successor, or
scheduled feed, but that source is pending written rights and has no adapter or
production approval. Google Places and Gemini Search Grounding are not
persistent acquisition sources. Gemini may only structure factual content from
a URL DTD already obtained lawfully, and AI confidence alone never publishes or
verifies a profile.

Canonical merging, delisting suppression, non-destructive writes, explicit
apply authority, machine-readable manifests, and `/ops` evidence remain
mandatory for both launch seeding and post-launch maintenance.

---

## 3. UI/UX Audit & Modern Friction-Free Interaction Architecture

### 3.1 Design System, Tokens & Earthy Luxe Palette
* **Token Remediations:** Semantic tokens mapped in `tailwind.config.js` and `index.css`:
  - Primary Ink: `#1A3A32` (`--dtd-ink` / `--ink-public`)
  - Secondary Ink: `#4A615A` (`--dtd-ink-2` / `--ink-secondary-public`)
  - Moss Accent: `#5C6D59` (`--moss`)
  - Terracotta Action / Interactive: `#9B4F31` / `#D06D4F` (`--terracotta`)
  - Warm Earthy Backgrounds: `#F5F2EB` (`--bg-public`), `#FAFAF7` (`--surface-public`)
  - Subtle Borders: `#E5DFD3` (`--line`)
* **Visual Language Alignment:** Standardize all routes on the canonical **Organic Earthy Luxe** layout (`hero-shell`, `card-public`, custom `PublicArt.jsx` illustrations), eliminating dark-card orbs and visual clutter.

### 3.2 Automation-Native & Friction-Free Dog Owner UX
1. **Interactive Visual Diagnostic Wizard (Zero Friction)**:
   - Card-based, reactive multi-step intake (dog age, issue pills like *Leash Reactivity*, *Puppy Socialisation*, *Separation Anxiety*, format *In-Home vs Facility*).
   - Instant client-side matching transitions with Framer Motion spring physics (no full page reloads).
   - Clear diagnostic match rationale: *"Why this trainer? 98% Issue Fit • Covers Richmond • In-Home Specialist"*.
2. **Mobile-First Luxury & Responsive Bottom Sheets**:
   - Mobile interactions leverage tactile bottom-sheet drawers (`vaul`) instead of intrusive nested modals.
   - Touch targets strictly exceed 44px with immediate haptic-style visual feedback.
3. **Sub-Second Suburb Filtering (`/melbourne/:suburb`)**:
   - Sticky filter pills (Puppy, Reactivity, Force-Free, In-Home) that filter directory listings instantly with micro-animations.

### 3.3 Modern Turnkey Dog Trainer UX
1. **10-Second Frictionless Profile Claiming**:
   - Prominent *"Claim this business"* badge on unclaimed profiles opens an accessible 6-digit OTP modal (`input-otp` with auto-focus and clipboard paste support).
   - Zero-password friction: Uses passwordless email magic links and SMS authentication.
2. **Direct Turnkey Booking Embeds (Pro Storefront)**:
   - Seamless inline embedding of Calendly, Acuity, or custom booking engines directly on the trainer's profile (`/t/:slug`), allowing owners to book without leaving DTD.
3. **Transformation Gallery & Media Showcase**:
   - Modern smooth carousels (`embla-carousel-react`) and masonry grids showcasing client before-and-after training videos and transformation galleries.
4. **Interactive ABN Government Trust Badge**:
   - Interactive popover on the *"✓ ABN Verified"* badge displaying live ABR entity type, registered postcode, and direct link to official government records (`abr.business.gov.au`).
5. **1-Click Stripe Billing & Customer Portal**:
   - Apple Pay / Google Pay / Australian card autofill via Stripe Checkout for instant Pro ($19/mo) and Suburb ($39/mo) upgrades.
   - Self-serve Stripe Customer Portal for 1-click plan management, tax invoice downloads, and cancellations.

### 3.4 Modern Operations Cockpit UX (`/ops`)
1. **1-Click Triage Cards**:
   - High-contrast dark glassmorphism cockpit (`[data-theme="admin"]`).
   - Exception items presented as self-contained action cards with keyboard shortcuts for 1-click approvals (`[Approve]`, `[Reject]`, `[Merge]`).
2. **Visual Suburb Scarcity Heatmap**:
   - Grid of Melbourne's ~300 suburbs with color-coded inventory indicators: `0/2 Open` (Green), `1/2 Urgency` (Amber), `2/2 Sold Out` (Red/Gray).
3. **Live Throughput Sankey Visualization**:
   - Real-time conversion velocity tracking across Melbourne: Demand $\rightarrow$ Intakes $\rightarrow$ Introductions $\rightarrow$ Outcomes $\rightarrow$ MRR.

### 3.5 Copywriting & Tone Standards
* **Australian English:** Enforce Australian spelling across all copy (`behavioural`, `specialise`, `programme`).
* **Marketing Heading Rule:** Zero trailing punctuation (`.` or `?`) in public H1/H2 marketing headings.
* **Public Language Guardrail:** Strip internal algorithm phrases (`Scoring…`, `confidence · 85%`, `follow-up spam`) from public-facing forms.

---

## 4. Modern OpenAI-Inspired Modular Education Architecture

### 4.1 The 3-Pane Unified Learning Hub (`/learn`)
Inspired by OpenAI's modular learning tracks and developer documentation, DTD's education lane is unified into an **open, distraction-free 3-pane interactive learning interface**:

```
                         OPENAI-STYLE 3-PANE LEARNING HUB
┌─────────────────────┬───────────────────────────────────────────┬───────────────────────┐
│ LEFT SIDEBAR        │ CENTER READING & INTERACTIVE CANVAS       │ RIGHT SIDEBAR         │
│ (Track & Progress)  │ (Distraction-Free Course Content)         │ (TOC & Specialist CTA)│
├─────────────────────┼───────────────────────────────────────────┼───────────────────────┤
│ • Progress Ring     │ 🏷️ Guide 1 • ⏱ 4 min read • Puppy Base     │ • On this page:       │
│ • Guide 1: Blueprint│ # Safe Home Setup: The Base Zone          │   - Objective         │
│   ✓ 1.1 Home Base   │                                           │   - Situation         │
│   • 1.2 Hazards     │ 🎯 **Expected Outcome**                   │   - What to Notice    │
│   • 1.3 Vet Prep    │ Stabilise home boundaries before day 1.   │   - Decision Rule     │
│   • Tools           │                                           │   - Action Checklist  │
│ • Guide 2: Transit. │ 📖 **Situation Scenario**                 │   - When to Get Help  │
│ • Guide 3: Empathy  │ Real-life home context and trigger points │                       │
│ • Guide 4: Social   │                                           │ ───────────────────── │
│ • Guide 5: Sync     │ 🔍 **What to Notice (Observation Points)**│ 🐾 **Need Local Help?**│
│ • Guide 6: Urban    │ Checklist of non-verbal puppy signals.    │ Facing puppy distress │
│ • Guide 7: Freedom  │                                           │ in Richmond?          │
│                     │ ⚠️ **Common Mistake (Caution Callout)**   │ [Find Puppy Classes →]│
│                     │ "Do not punish crate whining..."          │                       │
│                     │                                           │                       │
│                     │ ⚖️ **The Decision Rule (Key Principle)**  │                       │
│                     │ [Highlighted High-Contrast Rule Box]      │                       │
│                     │                                           │                       │
│                     │ ✅ **Interactive Action Checklist**       │                       │
│                     │ [ ] Set up crate in low-traffic corner    │                       │
│                     │ [ ] Prepare 3 enrichment chew toys        │                       │
│                     │                                           │                       │
│                     │ 🚩 **When to Seek Professional Help**     │                       │
│                     │ Specific clinical escalation thresholds.  │                       │
│                     │                                           │                       │
│                     │ 📋 **What to Record for Your Trainer**    │                       │
│                     │ Exact logs to bring to a consultation.    │                       │
│                     │                                           │                       │
│                     │ ───────────────────────────────────────── │                       │
│                     │ [← Previous Lesson]    [Next Lesson →]    │                       │
└─────────────────────┴───────────────────────────────────────────┴───────────────────────┘
```

### 4.2 Friction-Free Open Access & Soft Opt-In
1. **Zero Forced Paywall or Email Gate**: The entire 7-guide curriculum is **100% open and readable immediately**. Users can start reading without an account.
2. **Local Storage Persistence**: Checklists and reading progress auto-save to `localStorage` without requiring login.
3. **Progressive Value-Add Capture**: Owners are offered an optional email opt-in to:
   - Synchronize learning progress across mobile and desktop.
   - Download the printable PDF Cheatsheet & Checklist Pack.
   - Receive automated developmental milestone check-ins matched to their dog's age.

### 4.3 Direct Escalation Bridge to Local Trainers
Every lesson concludes with an explicit **Clinical Escalation Note** and **Trainer Readiness Checklist** that connects the owner's self-learning directly to the DTD directory:
* Lesson on Leash Pulling $\rightarrow$ Contextual link to *Reactivity & Loose-Leash Specialists in [User Suburb]*.
* Lesson on Home Separation $\rightarrow$ Contextual link to *In-Home Behavioural Consultants in [User Suburb]*.

### 4.4 Consolidation & Decommissioning of POCs
* **Single Canonical Route (`/learn` and `/learn/:guideSlug/:lessonSlug`)**: All educational content is rendered natively in the React application using Tailwind and Framer Motion.
* **Decommission External POCs**: The standalone Docusaurus site (`education-course-poc/`) and GitBook export (`education-gitbook-export-poc/`) are superseded by the integrated React `/learn` hub, ensuring zero tech drift.

---

## 5. Monetization Architecture & All-Inclusive Pricing Matrix

### 5.1 Rejection of Broken Industry Models
* **No Pay-Per-Lead (Bark/HiPages model rejected):** Trainers hate paying for dead leads and competing in price-cutting races.
* **No 15–20% Take Rate (Mad Paws/Rover model rejected):** High-ticket dog training ($150–$1,500+) causes aggressive off-platform disintermediation when commissions are taken.
* **Adopted Standard:** **Predictable Flat SaaS Storefront (Psychology Today Model) + Scarcity Suburb Sponsorship**.

### 5.2 All-Inclusive Standalone Tiers (No Add-On Base Fees)

All paid tiers are **flat and all-inclusive**. Purchasing Suburb Sponsorship ($39/mo) or Melbourne-Wide Sponsorship ($199/mo) **fully includes all Pro features ($19 value included)** with zero extra base fees. All prices are **GST inclusive**.

| Package | Total Monthly Cost (inc. GST) | Target User | Inclusions & Benefits |
| :--- | :--- | :--- | :--- |
| **Tier 0: Base Ingested** | **$0 / Free** (Perpetual) | Approved-source public supply | • Source-supported basic business details & unlinked URL<br>• Evidence-backed methods and specialty tags<br>• No copied Google review/rating content<br>• \"Claim this business\" badge |
| **Tier 1: Claimed & Verified** | **$0 / Free** (OTP Verified) | Onboarded / Claimed Trainers | • Verified identity badge<br>• Full ability to edit bio, photos, services, pricing<br>• Direct owner enquiry notifications & lead inbox<br>• Profile view analytics |
| **Tier 2: Pro Storefront** | **$19/mo** or **$149/yr** | Solo & Independent Trainers | • **Everything in Tier 1**, plus:<br>• **Gold \"Verified DTD Professional\" Trust Badge**<br>• **Direct Booking Embed** (Calendly / Acuity / Custom Intake)<br>• **Dofollow Website Link** & Social Channels (SEO authority)<br>• **Photo & Video Showcase Gallery** (client transformations)<br>• **Competitor ad suppression** on profile<br>• Priority boost in All-Melbourne directory ranking |
| **Tier 3: Suburb Featured Sponsor** | **$39/mo flat** (per suburb) | Local Facility & Park Trainers | • **Everything in Pro Storefront ($19 value INCLUDED)**, plus:<br>• **Pinned Top Spotlight** on `/melbourne/:suburb` (e.g. Richmond)<br>• 50/50 round-robin rotation for dual sponsors<br>• Priority match boost in Diagnostic Match Wizard for that suburb<br>• **Capped at max 2 sponsors per suburb** (high scarcity) |
| **Tier 4: Melbourne-Wide Sponsor** | **$199/mo flat** (citywide) | Mobile In-Home Consultancies | • **Everything in Pro Storefront ($19 value INCLUDED)**, plus:<br>• **Pinned Top of Main Directory** on `/trainers`<br>• **Featured across all 300 suburb pages** as *\"Melbourne-Wide Mobile Specialist\"*<br>• Top recommendation in citywide match requests<br>• **Capped at max 5 sponsors across Melbourne** |

### 5.3 Master Feature Inclusions Matrix

| Feature / Inclusion | Tier 0: Base Free | Tier 1: Claimed Free | Tier 2: Pro ($19/mo) | Suburb Sponsor ($39/mo flat) | Melbourne-Wide ($199/mo flat) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Cost (AUD inc. GST)** | **$0** | **$0** | **$19/mo** | **$39/mo** | **$199/mo** |
| Public Business Profile | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ |
| Categorized Methods & Specialties | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ |
| Verified DTD Review Signals | -- | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ |
| Edit Bio, Services & Pricing | $	imes$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ |
| Direct Lead Notifications | $	imes$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ |
| Profile View Analytics | $	imes$ | $\checkmark$ | $\checkmark$ | $\checkmark$ | $\checkmark$ |
| **Gold \"Verified Pro\" Badge** | $	imes$ | $	imes$ | $\checkmark$ | $\checkmark$ *(Included)* | $\checkmark$ *(Included)* |
| **Live Calendar / Booking Embed** | $	imes$ | $	imes$ | $\checkmark$ | $\checkmark$ *(Included)* | $\checkmark$ *(Included)* |
| **Dofollow SEO Website Link** | $	imes$ | $	imes$ | $\checkmark$ | $\checkmark$ *(Included)* | $\checkmark$ *(Included)* |
| **Photo & Video Portfolio Gallery** | $	imes$ | $	imes$ | $\checkmark$ | $\checkmark$ *(Included)* | $\checkmark$ *(Included)* |
| **Competitor Ads Removed on Profile** | $	imes$ | $	imes$ | $\checkmark$ | $\checkmark$ *(Included)* | $\checkmark$ *(Included)* |
| **General Directory Rank Boost** | $	imes$ | $	imes$ | $\checkmark$ | $\checkmark$ *(Included)* | $\checkmark$ *(Included)* |
| **Pinned Top of Target Suburb Page** | $	imes$ | $	imes$ | $	imes$ | $\checkmark$ (Max 2/suburb) | $\checkmark$ (All 300 Suburbs) |
| **Pinned Top of Main `/trainers` Page** | $	imes$ | $	imes$ | $	imes$ | $	imes$ | $\checkmark$ (Max 5 citywide) |

---

## 6. Refund Policy & Consumer Protections (ACL Compliance)

### 6.1 Trainer Subscription Refund Policy
* **14-Day Money-Back Guarantee (Monthly Plans):** If a trainer upgrades to Pro ($19/mo) or Suburb Sponsorship ($39/mo) and is unsatisfied within the first 14 days of their first billing cycle, they can request a 100% full refund.
* **30-Day Money-Back Guarantee (Annual Plans):** Full 100% refund if requested within 30 days of annual payment ($149/yr).
* **Self-Serve & 1-Click Execution:** The operator can execute a 1-click refund from the `/ops` console using the Stripe API, which immediately reverses charges, logs an audit record, and issues a formal tax credit note.

### 6.2 Dog Owner Protections & Service Mediation
* **Zero Direct Directory Fees:** Dog owners never pay DTD to browse, match, or contact trainers. Training fees are paid directly between owner and trainer.
* **Quality & Trust Guarantee:** If an owner reports severe trainer misconduct, unresponsiveness, or unverified claims, DTD conducts an investigation. If substantiated, DTD revokes the trainer's \"Verified Pro\" badge and can suspend the listing.

### 6.3 Australian Consumer Law (ACL) Compliance
* DTD explicitly operates under Schedule 2 of the *Competition and Consumer Act 2010 (Cth)*. All digital services provided with a fee are backed by statutory consumer guarantees that cannot be excluded by contract.

---

## 7. Catchment, Geography & Inventory Model

### 7.1 The 3 Catchment Types
1. **Hyper-Local / Facility-Based:** Base suburb + strict radius (e.g. Richmond + 5km).
2. **Regional Cluster:** Major geographic quadrant (e.g. Inner East, Northern Suburbs, Bayside).
3. **Melbourne-Wide Mobile:** Mobile in-home behavioural consultancies traveling across all Greater Melbourne.

### 7.2 Dynamic Suburb Inventory & Vacancies
* **Total Inventory:** ~300 Melbourne suburbs $	imes$ 2 sponsor slots = 600 potential sponsorship positions.
* **Real-Time Availability States:**
  - `0 / 2`: Status **Available** (Green)
  - `1 / 2`: Status **Only 1 Spot Remaining!** (Amber urgency)
  - `2 / 2`: Status **Sold Out — Join Suburb Waitlist** (Red/Gray)
* **Automated Waterfall Succession:** When a sold-out suburb has a cancellation:
  - System generates an exclusive 48-hour checkout token and emails Waitlist Position #1.
  - If unpurchased at $T+48	ext{h}$, the slot automatically cascades to Waitlist Position #2.
  - If all waitlisted trainers pass or the waitlist is empty, the slot reverts to public availability (`0/2` or `1/2`).
* **No Empty Pages:** If a suburb has 0 local sponsors, the page automatically renders Melbourne-wide mobile specialists and organic local trainers.

---

## 8. Multi-Surface Ranking Algorithms

### 8.1 All-Melbourne Search (`/trainers`, No Suburb Selected)
1. **Layer 1:** Melbourne-Wide Featured Sponsors ($199/mo, max 5, rotating).
2. **Layer 2:** Pro Verified Trainers ($19/mo) & Regional Sponsors ($99/mo), ordered by Composite Reputation Score:
   $$	ext{Score} = (	ext{Review Rating} 	imes \log(	ext{Review Count} + 1)) + 	ext{Profile Completeness}$$
3. **Layer 3:** Claimed & Active Free Trainers (Single-suburb sponsors appear here in the general citywide pool).
4. **Layer 4:** Ingested / Unclaimed Baseline Profiles.

### 8.2 Suburb-Specific Search (`/melbourne/:suburb`, e.g. Richmond)
1. **Top Pinned Spotlight:** Suburb Sponsors for Richmond ($39/mo, max 2, 50/50 round-robin rotation).
2. **Mobile Spotlight:** Melbourne-Wide Mobile Specialists servicing Richmond.
3. **Community Choice:** Highest-rated organic local trainer (unbuyable earned spot).
4. **Local Pro Trainers ($19/mo):** Located in/near Richmond, sorted by distance & rating.
5. **Organic Local Supply:** Claimed and unclaimed trainers in that suburb.

### 8.3 Diagnostic Match Wizard (Case-Based Fit)
$$	ext{Fit Score} = 	ext{Issue Compatibility (40\%)} + 	ext{Method Match (25\%)} + 	ext{Location / In-Home Match (20\%)} + 	ext{Pro Verification (15\%)}$$
* Returns top 3 tailored recommendations with plain-English clinical rationale.

---

## 9. Fairness & Anti-Monopoly Governance

To prevent well-funded agencies from buying up the platform:
1. **Hard Suburb Ownership Cap:** A single trainer/business can sponsor a **maximum of 3 to 5 suburbs** total.
2. **Per-Suburb Cap:** Max **2 sponsors per suburb**, with no single business holding both slots.
3. **Location & Specialty Eligibility Gate:** Trainers can only sponsor suburbs within their verified physical location or travel radius. Clinical/specialty fit always overrides advertising.
4. **The Unbuyable \"Community Choice\" Spot:** Every suburb reserves a top placement for the highest-rated local trainer based purely on verified client reviews.
5. **50/50 Fair Rotation:** Dual sponsors in a suburb receive equal 50/50 round-robin impression weighting.
6. **Quality-Gated Renewals & Response Rate SLA:**
   - Sponsors must maintain a $>75\%$ inquiry acknowledgment rate.
   - Measured via the masked relay proxy or Trainer Portal (`[Mark as Contacted]` within 7 days).
   - If $\ge 3$ consecutive inquiries are ignored over 30 days, automated renewal is paused and flagged in `/ops`.

---

## 10. Pre-Implementation Gap Resolutions & Edge-Case Protocols

| Gap Area | Resolved Architecture | Implementation Detail |
| :--- | :--- | :--- |
| **Ingestion Deduplication** | Canonical entity matching | Match on normalized phone number, website domain, or ABN. Merge overlapping listings into one profile. |
| **Delisting & Suppression** | 1-Click Self-Delisting & Suppression Table | Opted-out trainers are stored in `db.delisted_entities` so background scrapers never re-harvest or re-publish them. |
| **Ownership Disputes** | Automated `CLAIM_DISPUTED` state lock | Multiple claim attempts freeze the profile and route to `/ops` for ASIC extract / photo ID review. |
| **Landline Claims** | Document verification exception | If no mobile SMS or domain email exists, trainer uploads ABN proof for 1-click review in `/ops`. |
| **SEO Canonicalization** | Clean SEO URLs + dynamic sitemap + JSON-LD | Primary `<link rel=\"canonical\">` on `/t/:slug`; Suburb hubs render `ItemList` and `LocalBusiness` JSON-LD schema. |
| **Match Fallback** | 3-stage radius expansion | If 0 local matches exist, expands to Regional Quadrant $\rightarrow$ Melbourne-Wide Mobile Specialists. |
| **Trainer Auth** | Passwordless Magic Links & SMS OTP | Secure, zero-password login via email magic link or SMS OTP. |
| **Review Integrity** | Verified client reviews only | DTD review signals come from verified DTD introductions; Google Places reviews, ratings, and sentiment are not copied into trainer records. |
| **Crawler Ethics** | Polite source rate limits | User-Agent `DTD-Bot/1.0`, max 1 req / 2 sec per domain, approved official business websites only, with ABR used for identity/status evidence. |
| **Australian Tax (GST)** | Displayed pricing is GST-inclusive | All pricing clearly marked as GST inclusive ($19, $39, $199 AUD inc. GST). |

---

## 11. Automated Communication Triggers Matrix

```
                               COMMUNICATION TRIGGERS MAP
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. TRAINER LIFECYCLE TRIGGERS                                                             │
│ • Unclaimed Lead Alert (Email): \"A dog owner in [Suburb] requested a consultation. Claim   │
│   your profile to view details & reply.\"                                                  │
│ • Claim OTP / Magic Link (Email/SMS): 6-digit verification code to claim profile.         │
│ • Claim Verified Welcome (Email): Login magic link + guide to profile customization.      │
│ • Claimed Lead Alert (Email/SMS): Instant notification of new consultation inquiry.       │
│ • Pro Trial Expiry Warning (Email - Day 23): \"Your trial ends in 7 days (X views logged).\"│
│ • Suburb Sponsorship Vacancy Alert (Email): \"Spot opened in [Suburb] (48h priority window)\"│
│ • Stripe Invoices & Receipts (Email): Monthly/Annual tax invoices with ABN/GST details.   │
│ • Payment Failed Warning (Email): Card failure alert with 14-day update grace period.     │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. DOG OWNER LIFECYCLE TRIGGERS                                                           │
│ • Diagnostic Match Report (Email): Copy of matched trainers, diagnostic summary & links.  │
│ • Consultation Sent Confirmation (Email): \"Your message was delivered to [Trainer Name].\" │
│ • T+7 Outcome Check-in (Email): \"Did you connect with [Trainer Name]?\" (Logs conversion).  │
│ • T+14 Verified Review Invite (Email): \"Share your feedback for [Trainer Name].\"           │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. OPERATOR EXCEPTION TRIGGERS (/ops Alerts)                                              │
│ • Ingestion Anomaly Alert: Low confidence score or conflicting business data.             │
│ • Unmatched Claim / Dispute Exception: Multiple claimants or ABN document uploaded.      │
│ • Stalled Introduction Alert: Intro with 0 trainer response after 7 days.                 │
│ • Stripe Dispute / Chargeback Alert: Immediate alert if a payment is disputed.            │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Platform Integrations, Hardening Contracts & Complete Cost Matrix

### 12.1 Platform Integrations Summary

```
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ PLATFORM / SERVICE           │ FUNCTION & WORKFLOW          │ INTEGRATION METHOD           │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Stripe Billing & Checkout**│ Subscriptions, Pro checkout, │ Stripe API, Checkout Sessions│
│                              │ Suburb sponsorships, Webhooks│ & Webhook listener           │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Resend**                   │ Transactional email delivery │ REST API via                 │
│                              │ (Leads, OTP, Follow-ups)     │ `backend/services/notif.py`  │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Twilio / MessageMedia**    │ Australian Mobile SMS OTP    │ REST API for instant mobile  │
│                              │ verification for claims      │ phone verification           │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Google Places API**        │ Reserved for separately      │ Not a persisted trainer-     │
│                              │ approved compliant UX uses   │ listing ingestion source     │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **ABR Lookup API (abr.gov)** │ Business registration and    │ Australian Business Register │
│                              │ legal entity verification    │ Web Services API             │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Cloudinary / AWS S3**      │ High-res trainer portfolio,  │ Direct authenticated upload  │
│                              │ logo, and transformation media│ for trainer galleries        │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

### 12.2 Third-Party Integration Hardening Contracts

```
                       INTEGRATION HARDENING CONTRACTS
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. TURNKEY BOOKING EMBED CONTRACT (Calendly / Acuity / Custom Schedulers)       │
│ • Protocol Validation: Enforce strict `https://` URLs; reject `javascript:`/raw │
│ • Sandboxing: `sandbox="allow-scripts allow-same-origin allow-popups allow-forms"`│
│ • Referrer Policy: `referrerpolicy="no-referrer-when-downgrade"`                │
│ • Graceful Fallback: If URL is non-embeddable, auto-render verified CTA:       │
│   `[Book Consultation with Trainer ↗]` opening via `target="_blank" rel="noopener"`│
├─────────────────────────────────────────────────────────────────────────────────┤
│ 2. SMS OTP & ANTI-FRAUD RATE-LIMIT CONTRACT (Twilio / MessageMedia)             │
│ • Toll-Fraud Guard: Max 3 OTP SMS requests per IP and per Phone per 15 minutes. │
│ • Dual-Channel Fallback: If SMS fails or times out (10s), UI offers instant     │
│   1-click fallback: "Didn't receive SMS? Send verification code to email".       │
│ • Mobile Normalization: Enforce Australian E.164 (`+614...`) before API call.   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 3. GOVERNMENT BUSINESS REGISTER CONTRACT (ABR Web Services)                     │
│ • Offline Mathematical Pre-Filter: ATO Modulus 89 checksum (0ms offline check). │
│ • JSONP Unwrapping: Built-in regex parser unwraps `callback({...})` to raw JSON.│
│ • Government Quota Guard: 30-day cache (`db.abn_cache`) drops API calls by >95%.│
│ • Trading Name Sunsetting: Fall back to Sole Trader legal name token matching   │
│   when post-October 2025 `business_names` array is empty.                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 4. STRIPE WEBHOOK & B2B TAX CONTRACT (Stripe Australia)                         │
│ • Cryptographic Verification: `stripe.Webhook.construct_event()` with raw body. │
│ • Replay Protection: Dedup events against `db.stripe_events` via `event.id`.    │
│ • Australian Tax Provisioning: `stripe.Customer.create_tax_id(type="au_abn")`   │
│   attaches verified ABN to generate ATO-compliant 10% GST tax invoices.         │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 5. MEDIA OPTIMIZATION & CDN CONTRACT (Cloudinary / AWS S3)                      │
│ • Client Validation: Max 5MB per upload; accept strictly `image/jpeg,png,webp`. │
│ • Auto-Format & Quality: Deliver via CDN with `f_auto,q_auto,w_800` transforms. │
│ • Core Web Vitals: All portfolio images render with `loading="lazy"` & width/ht.│
├─────────────────────────────────────────────────────────────────────────────────┤
│ 6. MODERN UI COMPONENT CONTRACTS (`vaul`, `input-otp`, `embla-carousel-react`)  │
│ • Responsive Drawer Switch: `< 768px` renders tactile bottom-sheet drawer       │
│   (`vaul`); `≥ 768px` renders centered Radix Dialog modal.                      │
│ • Accessible OTP: Strict numeric `inputMode="numeric"` with clipboard paste and │
│   auto-focus progression across all 6 slots.                                    │
│ • Smooth Carousel: Touch-drag physics with keyboard navigation & aria labels.   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 12.3 Infrastructure Cost Matrix & Unit Economics (GCP + Firebase)

The runtime infrastructure is unified on Google Cloud Platform and Firebase (detailed in [DTD_GOOGLE_CLOUD_MIGRATION_RUNBOOK.md](DTD_GOOGLE_CLOUD_MIGRATION_RUNBOOK.md)):

```
                               MONTHLY COST BREAKDOWN (AUD)
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ PLATFORM / SERVICE           │ PRICING MODEL & FREE TIER    │ ESTIMATED COST (LAUNCH / MO) │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ **Google Cloud Run**         │ 2M requests/mo free          │ **$0.00** (Under free tier)  │
│ **Cloud Tasks & Scheduler**  │ 1M tasks free; 3 jobs free   │ **~$0.45 AUD**               │
│ **Firebase Hosting (Multi)** │ 10 GB storage free           │ **$0.00** (Under free tier)  │
│ **Firebase Phone Auth**      │ **10,000 free SMS OTPs / mo**│ **$0.00** (Free perpetual)   │
│ **Google Gemini 1.5 Flash**  │ 1,500 free requests / day    │ **~$0.50 AUD**               │
│ **Google Maps Platform**     │ **$200 USD/mo free credit**  │ **$0.00** (Covered by credit)│
│ **MongoDB Atlas (GCP Sydney)│ Free M0 / Serverless         │ **$0.00 - $15.00 AUD**       │
│ **Resend (Email)**           │ Free 3,000 emails / month    │ **$0.00** (Under free tier)  │
│ **Stripe Australia**         │ 1.75% + 30¢ per AU card sale │ **$0 fixed** (Pay-per-sale)  │
│ **ABR Government API**       │ **100% Free** (ATO Gov API)  │ **$0.00** (Free perpetual)   │
│ **.com.au Domain Name**      │ $20 AUD / year               │ **~$1.70 AUD / month**       │
├──────────────────────────────┴──────────────────────────────┼──────────────────────────────┤
│ **TOTAL ESTIMATED FIXED RUNNING COST**                      │ **~$2.65 - $17.00 AUD / mo** │
│ **WITH GOOGLE FOR STARTUPS CREDITS ($2,000 - $200,000 USD)**│ **$0.00 AUD / month**        │
└─────────────────────────────────────────────────────────────┴──────────────────────────────┘
```

| Operating Scale | Paid Subscriptions | Monthly Revenue (MRR) | Fixed Costs | Net Gross Margin |
| :--- | :---: | :---: | :---: | :---: |
| **Launch Baseline** | 0 paid (Free Tier) | **$0 AUD** | **~$2.65 AUD / month** | N/A |
| **Breakeven Point** | **1 Suburb Sponsor ($39/mo)** | **$39 AUD** | **~$2.65 AUD / month** | **+93% Net Margin** |
| **Early Growth** | 20 Pro + 10 Suburb | **$770 AUD** | **~$5.00 AUD / month** | **+99% Net Margin** |
| **Mature Melbourne** | 100 Pro + 60 Suburb + 3 Citywide | **$4,837 AUD** | **~$25.00 AUD / month**| **+99% Net Margin** |

*Note: Integration hardening contracts are detailed in [DTD_AUTOMATION_AND_INTEGRATION_SPEC.md](DTD_AUTOMATION_AND_INTEGRATION_SPEC.md).*

---

## 13. Competitive Landscape & Startup Capital / Cloud Credit Strategy

### 13.1 Competitive Landscape & Market Positioning

| Competitor / Platform | Operating Model & Monetization | Critical Flaws & Trainer Pain Points | DTD Competitive Advantage |
| :--- | :--- | :--- | :--- |
| **Bark.com / Oneflare** | Pay-per-lead model ($15–$40 per lead credit). Broadcasts lead to 5 competitors. | • High churn; trainers pay for dead leads.<br>• Leads to aggressive price-slashing races. | **Zero Lead Fees**: Flat SaaS storefront + scarcity sponsorship. 100% direct owner connection. |
| **Mad Paws / Rover / PetBacker** | 15%–20% commission take-rate on every transaction. | • High disintermediation on $500–$1,500 training.<br>• Primarily designed for dog walking/boarding. | **0% Commission**: Trainers keep 100% of client fees. Tailored to clinical dog training. |
| **GoodPup** | Direct-to-consumer 1-on-1 video app ($34/week subscription). | • Virtual only; cannot solve severe reactivity or in-person behavioural cases. | **Local & In-Person First**: Matches owners with verified physical/in-home Melbourne trainers. |
| **APDT / NDTF / VDTA Association Lists** | Non-profit static HTML directory lists. | • Zero search UX, no reviews, no diagnostic wizard, no booking tools. | **Modern Automation**: Instant diagnostic intake, ABR verification, and live booking embeds. |
| **Psychology Today (Analogous Leader)** | Flat subscription directory ($29.95 USD/mo) for mental health practitioners. | • N/A (Gold standard in healthcare). | **Category Creator**: DTD executes the proven Psychology Today model for the dog training vertical. |

### 13.2 Startup Cloud Credits Strategy ($50,000+ Non-Dilutive Capital)

```
                       STARTUP CLOUD CREDIT PLAYBOOK
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. GOOGLE FOR STARTUPS CLOUD PROGRAM                                            │
│ • Value: $2,000 USD initial credit (up to $200k-$350k for funded/AI startups).  │
│ • Covers: Google Maps Places API, Cloud Run, Gemini AI embeddings.              │
│ • Application: Apply via cloud.google.com/startup with company website & domain. │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 2. MICROSOFT FOR STARTUPS FOUNDERS HUB (Open to All Builders)                   │
│ • Value: $1,000 to $5,000 USD in Azure & OpenAI credits (scales to $150k).      │
│ • Perks: Free GitHub Enterprise, LinkedIn Premium, and Azure OpenAI tokens.     │
│ • Application: Instant access with zero external funding required via MS Hub.   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 3. MONGODB FOR STARTUPS                                                         │
│ • Value: Up to $5,000 USD in MongoDB Atlas credits (valid for 12 months).       │
│ • Application: Apply via mongodb.com/solutions/startups.                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 4. POSTHOG FOR STARTUPS                                                         │
│ • Value: $50,000 USD in telemetry, analytics, and session replay credits.       │
│ • Application: Apply via posthog.com/startups.                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 5. STRIPE STARTUP PROGRAM                                                       │
│ • Value: Fee-free payment processing on the first $20,000 – $50,000 AUD volume. │
│ • Application: Available through startup accelerators and incubators.           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 13.3 Australian & Victorian Government Grants (Non-Dilutive Funding)
1. **LaunchVic (Victoria's Startup Agency)**:
   - State-backed grants, pre-accelerator funding, and AI/DeepTech founder initiatives supporting Victorian tech startups.
2. **Australian R&D Tax Incentive (AusIndustry / ATO)**:
   - **43.5% refundable cash tax offset** on eligible R&D software expenditure (algorithmic diagnostic matching, heuristic web scrapers, automated multi-source deduplication).
3. **Leading ANZ Accelerators & Pre-Seed Funds**:
   - **Startmate**: Premier ANZ tech accelerator ($120k AUD SAFE investment).
   - **Antler Melbourne**: Early-stage venture generator with dedicated Victorian cohorts.
   - **Skalata Ventures**: Melbourne-based seed fund supporting operational tech platforms.

---

## 14. Autonomous Post-Launch Engine & Operator Role in `/ops`

### 14.1 Autonomous Engine (95%+ of Operations)
* **Ingestion:** An approved licensed source supplies candidates $\rightarrow$ factual source evidence and optional Gemini structuring are validated $\rightarrow$ ABR, geographic, dedupe, suppression, and quality gates produce an explicitly authorised publish-or-hold decision. AI confidence alone never publishes.
* **Claiming:** Instant OTP / magic link sent to public domain/email on file $\rightarrow$ auto-provisions portal.
* **Monetization:** Stripe Checkout $\rightarrow$ Webhook upgrades database tier instantly $\rightarrow$ Stripe handles recurring dunning and renewals.
* **Follow-Ups:** Automation worker sends T+7 day check-ins to owners, logging conversions automatically.

### 14.2 Operator's Role in `/ops` (10–15 Minutes/Week)
* **MRR & Throughput Observability:** Monitor Demand $\rightarrow$ Supply $\rightarrow$ Matches $\rightarrow$ Revenue in real time.
* **Claim Exceptions (1-Click):** Review personal email claims with attached ABN proofs.
* **Dispute Resolution:** Resolve rare duplicate business claims.
* **Refund Triage (1-Click):** Issue immediate Stripe refunds for eligible guarantee requests.
* **VIP Grants:** Issue 1-click complimentary founding partner sponsorships to anchor trainers.

---

## 15. The 4-Task Code Improvement Plan & Verification Gates

> **Sequential Execution Protocol:** Tasks 1 through 4 represent the mandatory local code improvement plan. All 4 tasks must be 100% completed, verified, and cleared before commencing the infrastructure move to the Google ecosystem.

---

### Task 1: Deadweight Pruning & Artificial Gate Removal

* **Objective:** Remove obsolete dynamic pricing code, failed invoice retry loops, and artificial 403 blocks that prevent public directory browsing and matching.
* **Target Files:**
  - `backend/server.py`: Remove `_require_public_matching` dependency and unblock `/api/match`.
  - `backend/services/engine.py`: Remove `recompute_pricing` (90s dynamic fee loop) and `run_billing_recovery` (30m $5 invoice retry loop) from `schedule_all`.
  - `backend/services/claim_state.py`: Remove or neutralize marketing claim restrictions (`STATE_0` to `STATE_4`).
  - `backend/services/engine.py`: Clean legacy `$65` fee conversion billing from `promote_inferred_conversions`.
* **Completion Criteria & Testable Exit Gates:**
  1. `POST /api/match` and `GET /api/trainers` execute and return HTTP 200 without throwing HTTP 403 Forbidden under default production configuration.
  2. `backend/services/engine.py` runs without scheduling `recompute_pricing` or `run_billing_recovery`, and background worker starts without attempting to run those two loops.
  3. No remaining endpoints or services depend on `claim_state.py` or obsolete $5 intro fee environment variables (`FIXED_INTRO_FEE_CENTS`).
  4. All existing backend tests in `backend/tests/` pass with zero regressions (`exit code 0`).

---

### Task 2: Schema Expansion, ABN Engine & Claim Endpoints

* **Objective:** Expand the Trainer data model, integrate the verified ABN Modulus 89 validator and ABR client from `abn-automation-poc/`, and add OTP profile claiming.
* **Target Files:**
  - `backend/server.py`: Update `Trainer` and `SubmissionIn` Pydantic models with expanded fields (`tier`, `claim_status`, `abn`, `abn_status`, `abn_verified`, `training_philosophy`, `specialties`, `service_formats`, `serviced_suburbs`, `catchment_type`, `booking_url`, `gallery_images`, `sponsored_suburbs`, `review_summary`).
  - `backend/services/abn_validator.py`: Port ATO Modulus 89 checksum validator from `abn-automation-poc/abn_validator.py`.
  - `backend/services/abr_client.py`: Port ABR Web Services client with 30-day caching from `abn-automation-poc/abr_client.py`.
  - `backend/server.py`: Implement `POST /api/trainers/{id}/claim` (generates 6-digit OTP, sets `claim_status="pending_verification"`, dispatches OTP via Resend email / SMS) and `POST /api/trainers/{id}/claim/verify` (validates OTP, transitions `claim_status="claimed"`, returns auth session).
* **Completion Criteria & Testable Exit Gates:**
  1. `backend/services/abn_validator.py` validates all 11-digit ATO Modulus 89 test vectors (accepts valid VIC ABNs, rejects invalid checksums and short strings).
  2. `POST /api/trainers/{id}/claim` on an unclaimed trainer generates a secure 6-digit OTP code, stores it with 15-minute TTL, and returns HTTP 200 with masked contact destination.
  3. `POST /api/trainers/{id}/claim/verify` with the correct OTP code updates `db.trainers` to `claim_status="claimed"`, sets `tier="claimed"`, and returns HTTP 200 with a valid session token.
  4. Submitting an incorrect OTP code returns HTTP 400 with a descriptive error message and does not alter `claim_status`.
  5. Newly inserted or updated trainer documents in MongoDB persist all expanded schema fields without serialization or validation errors.

---

### Task 3: Frontend Storefront Redesign, Design Tokens & Ops Bug Fix

* **Objective:** Map missing design tokens, redesign the trainer profile into a modern digital storefront with an OTP claim modal, and fix the `/ops` pipeline view bug.
* **Target Files:**
  - `frontend/tailwind.config.js`: Define missing semantic tokens (`dtd-heading`: `#1A3A32`, `dtd-content`: `#4A615A`, `dtd-border`: `#E5DFD3`, `dtd-moss`: `#5C6D59`, `dtd-terracotta`: `#9B4F31`).
  - `frontend/src/pages/TrainerDetail.jsx`: Redesign profile layout into a standalone storefront featuring:
    - Business name, base suburb, and service radius.
    - Badges (ABN Verified with popover, Verified Pro).
    - Specialties, training philosophy, and service formats.
    - Verified DTD review signals from attributable DTD introductions only.
    - Prominent **"Is this your business? Claim this profile"** banner (for unclaimed profiles).
    - 6-digit OTP claim modal (`input-otp` component with auto-focus and clipboard paste).
    - Booking embed / calendar CTA (for Pro profiles).
  - `frontend/src/pages/Ops.jsx`: Fix view switch bug around line 435 by ensuring `{activeView === "pipeline_flow" && <PipelineFlowView snap={snap} />}` renders properly without causing a blank screen.
* **Completion Criteria & Testable Exit Gates:**
  1. Frontend compiles with zero build errors (`yarn build` / `npm run build` succeeds).
  2. Navigating to `/t/:slug` or `/t/:id` renders the redesigned storefront layout with `PublicHeader` and `PublicFooter` using the canonical Earthy Luxe palette.
  3. For unclaimed profiles, clicking "Claim this business" opens the accessible OTP claiming modal and handles the 6-digit verification flow cleanly.
  4. In `/ops`, clicking the "Pipeline Flow" navigation tab displays the pipeline flow diagram instead of a blank screen.
  5. Zero missing Tailwind class warnings or broken CSS variables appear in the browser console.

---

### Task 4: Stripe SaaS Subscriptions & Greater Melbourne Supply Expansion

* **Objective:** Preserve flat Stripe SaaS subscriptions and expand the accepted launch baseline toward 100+ authentic profiles only after a licensed discovery source is approved and implemented.
* **Target Files:**
  - `backend/services/stripe_billing.py`: Implement `create_checkout_session(trainer_id, tier, suburb=None, interval="month")` generating Stripe Checkout sessions with line items matching the flat pricing matrix and attaching `stripe.Customer.create_tax_id(type="au_abn")`.
  - `backend/services/stripe_billing.py`: Update webhook handler to process `checkout.session.completed`, `customer.subscription.created/updated/deleted`, and `invoice.payment_succeeded`.
  - `backend/data/melbourne_trainers_seed.json`: Preserve the accepted 20-profile launch batch; future expansion must originate from the approved licensed-feed pipeline.
  - `scripts/seed_melbourne_trainers.py`: Create standalone idempotent seeding script (`--dry-run` and `--apply`).
* **Completion Criteria & Testable Exit Gates:**
  1. `POST /api/trainer/billing/checkout` returns a valid Stripe Checkout session URL configured with the selected tier ($19/mo, $39/mo, or $199/mo inc. GST).
  2. Stripe webhook handler successfully processes `customer.subscription.created` events, updates the trainer's `tier` to `"pro"` or `"suburb_sponsor"`, attaches `stripe_subscription_id`, and stores the active tier in MongoDB.
  3. An explicitly authorised `python3 scripts/seed_melbourne_trainers.py --apply --publish-qualified` run applies only attributable, active-ABR, quality-qualified candidates idempotently; the 100+ expansion is not a website-launch prerequisite.
  4. Navigating to `/trainers` and major suburb pages (`/melbourne/richmond`, `/melbourne/brunswick`, `/melbourne/st-kilda`) displays populated, accurate listings with working filter pills.
  5. Running the seed script a second time is completely idempotent (0 duplicate records created, existing claimed profiles preserved).

---

## 16. Post-Improvement Phase: Google Ecosystem Migration

Once Tasks 1 through 4 are 100% completed, tested, and cleared, proceed to the infrastructure migration as documented in the canonical runbook:  
📄 **[DTD_GOOGLE_CLOUD_MIGRATION_RUNBOOK.md](DTD_GOOGLE_CLOUD_MIGRATION_RUNBOOK.md)**

* **Phase 2.1:** Google Cloud Run Containerization (FastAPI Backend on Sydney `australia-southeast1`).
* **Phase 2.2:** Cloud Scheduler & Cloud Tasks (Autonomous triggers & Outbox queue).
* **Phase 2.3:** Firebase Hosting Deployment (`dogtrainersdirectory.com.au` and `learn.dogtrainersdirectory.com.au`).
* **Phase 2.4:** Firebase Phone Authentication (10,000 free SMS verifications/month).
* **Phase 2.5:** Google Gemini 1.5 Flash Integration (AI parsing and diagnostic matching).
