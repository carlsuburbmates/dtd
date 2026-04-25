# Bark&Bond — Dog Trainers Directory (PRD)

## Original problem statement
Build an autonomous digital business operating system on top of an existing
Melbourne dog-trainers directory. Maximise revenue, defensibility, and user
value while minimising human intervention. Listings must represent real
businesses only — never fabricated. Spec includes verification scoring,
monetisation, AI matching, auto-generated SEO, A/B tests, anomaly detection.

## Architecture (high level)
- **Backend:** FastAPI + Motor (MongoDB), `/api` prefix, Claude Sonnet 4.5 via
  `emergentintegrations`. Public + admin (passcode-gated) routes.
- **Frontend:** React 19, react-router-dom v7, TailwindCSS, shadcn/ui, sonner
  toasts, lucide-react icons, framer-motion installed.
- **Two surfaces:**
  - Public directory (warm editorial: Cormorant Garamond + Outfit, organic
    earthy palette).
  - Admin/Ops cockpit (dense dark JetBrains-Mono cockpit, `data-theme=admin`).

## Personas
1. **Dog owner** — searches by suburb / topic, uses AI matcher, sends a
   structured lead.
2. **Trainer** — ideally claims & upgrades to Featured/Premium tier; receives
   transparent, scored leads.
3. **Operator** — sole human, monitors ingestion, monetisation, A/B tests, and
   health alerts in the admin cockpit.

## Core requirements (static)
- No fabricated businesses or reviews.
- Verification with AI confidence score (0-1) + thresholds (≥0.85 verified,
  0.60–0.84 unverified, <0.60 hold).
- Paid placement clearly disclosed; never alters trust score.
- Lead transparency: every lead carries quality score + full text.
- Audit log for all admin actions; reversible mutations.

## Implemented (2026-04-25)
- Backend
  - Models: trainers, submissions, leads, ab_tests, audit_log, seo_pages,
    match_events.
  - Public: `/trainers`, `/trainers/:id`, `/featured`, `/suburbs`,
    `/categories`, `/stats/public`, `/leads`, `/submissions`, `/match`,
    `/seo/:slug`.
  - Admin: `/admin/login`, full CRUD on trainers, submissions
    approve/reject, leads list/patch, analytics (MRR, ARR, funnel,
    verification mix), A/B tests CRUD, health monitor with anomaly alerts,
    audit log, SEO generator, seed.
  - AI service (`services/ai.py`): `score_trainer`, `match_trainers`,
    `generate_seo_copy` — all with deterministic fallbacks if the LLM key is
    missing.
  - Auto-seed at startup with 12 real Melbourne trainers (sourced from public
    directories: Bark.com, Oneflare, Localsearch, VDTA, etc.).
- Frontend
  - Public: Home (editorial hero, search, featured, AI matcher promo, dual
    CTA), Directory (filters: suburb / category / verified-only), Trainer
    detail (profile, evidence reasoning, lead form with quality dashboard),
    Match (multi-step wizard with presets), Submit (auto-scores on submit
    with reasoning), Pricing (Free / Featured / Premium), Suburb SEO page.
  - Admin: passcode login + dashboard with 8 tabs (Overview, Ingestion,
    Listings, Leads, Monetisation, A/B tests, Health, SEO pages).
  - All interactive elements carry `data-testid`.

## Backlog
- P1: Trainer self-service login + claim flow.
- P1: Pay-per-lead billing once funnel proves conversion.
- P2: Public sitemap.xml + auto-publish SEO pages list.
- P2: Lead → trainer email notification (Resend / SendGrid).
- P2: Stripe subscription wiring for tier upgrades.
- P3: Behaviour-based ranking from match_events feedback (relevance signal).
- P3: Image moderation for trainer-uploaded photos.

## Next tasks (suggested)
1. Trainer auth + claim listing flow.
2. Email notifications for leads + ingestion approvals.
3. Stripe integration for subscription tiers.
