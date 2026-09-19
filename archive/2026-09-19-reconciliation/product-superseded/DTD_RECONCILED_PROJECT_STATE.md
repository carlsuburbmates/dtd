# DTD Reconciled Project State

**Purpose:** this document reconciles the accumulated planning conversation
against the verified current-state audit and owner decisions through
18 September 2026. The named
`DTD_CANONICAL_TARGET_STATE_SPECIFICATION.md` does not exist in this repository
or its Git history and must not be treated as an authority source.

The three states below are kept deliberately separate and must not be
collapsed into one roadmap.

---

## PART 1 — CURRENT STATE (verified, descriptive only)

As of the 18 September 2026 implementation:

- **Deployed and publicly live**, but commercially unlaunched. Main site
  and API are healthy in production; Stripe is in test mode; zero active
  paid sponsor positions; refund execution is disabled.
- **Trainer data:** 45 documents total, 34 published across regions, 30
  published in the active Greater Melbourne region. Of those 30: 20 have
  structured official-source provenance (unclaimed), 10 lack structured
  provenance, 1 uses an `.example.com` stub source, 3 are marked
  `discovery_seed`, 6 rely on aggregator (Bark/Oneflare) evidence. This is
  a mixed dataset, not a clean set of real claimed users.
- **Canonical suburb asset now exists in the repository.** The approved
  `backend/data/dtd_melbourne_suburbs.v1.json` contains 539 records.
  `/api/config` reads a complete seeded `suburbs` collection when available and
  otherwise fails soft to that versioned asset; it no longer derives canonical
  geography from the current trainer sample. The local `dtd` database has been
  seeded idempotently with all 539 rows; production seeding remains a separate
  rollout action and must not be inferred from local evidence.
- **Pricing tiers implemented:** Free/Core $0, Pro $19/mo or $149/yr,
  Suburb Sponsorship $39/mo, Melbourne-Wide $199/mo. No $99 Regional
  Sponsor tier exists. A dormant, unrelated $99/yr "Founding Verified
  Profile" string exists in inactive copy only.
- **Diagnostic matching keeps paid status out of fit scoring.** The AI prompt
  strips tier/billing fields and the deterministic fallback has no paid-status
  term. After fit scoring, paid tier is used only within a named five-point
  comparable-fit band; outside that band, fit alone determines order.
- **Refund logic is interval-based** (14 days monthly / 30 days annual),
  which already covers Melbourne-Wide monthly automatically — but
  execution is disabled (`ENABLE_OPS_STRIPE_REFUNDS` unset → 503), and
  `/ops` has no refund/cancel action in the UI.
- **Suburb sponsor caps:** 2 per suburb and 4 sponsored suburbs per business.
  `SPONSOR_MAX_SUBURBS_PER_TRAINER` remains configurable only within the
  existing 3–5 safety bounds; the canonical default is 4.
- **Pro trial:** a genuine 30-day Stripe Pro-subscription trial is implemented.
  Eligibility begins only when Stripe is in live mode and
  `STRIPE_LIVE_ANCHOR_AT` is set. Trainers claimed/registered before that
  timestamp are outside the cohort. Stripe owns the trial dates, webhook state
  is persisted, repeat trials are prevented, and the day-23 warning is an
  idempotent scheduled workflow visible through notification and system state.
- **Education:** The First Leash is the sole education implementation in the
  separate `DTD-education-extended` repository. Main DTD contains only the
  branded outbound bridge and legacy-route redirects; all duplicated education
  pages, APIs, curriculum, POCs and education-only assets were deleted rather
  than archived. The return bridge is static and query-free.
- **Ops tooling:** a bespoke, passcode-gated `/ops` React app already
  exists (overview, pipeline, work queue, supply, messages, billing/
  reactivation, recent changes, system activity, sponsor inventory) — but
  has no refund/cancel action. PostHog is wired client-side. Sentry is
  configured but does not initialise in the deployed API process (only in
  an undeployed worker). No MongoDB Atlas Charts integration exists.
- **SEO/indexation is not implemented.** No per-suburb listing count,
  word count, computed robots state, or Search Console sync. `/sitemap.xml`
  and `/robots.txt` both incorrectly return the SPA's `index.html`. Only 2
  `seo_pages` records exist.
- **Known critical issues outside this completed work package:**
  - Main DTD's CI does not run the frontend test suite or production
    build, only package metadata checks.
  - Some existing docs are self-contradictory against their own repo
    (e.g. `PROJECT_STATE.md` claims no tests exist; 14 passing tests do).

---

## STANDING PRODUCT AND OPERATING INVARIANTS

These constraints apply to every current and future implementation:

1. **Free/no-commission:** dog owners never pay DTD to browse, match, or
   contact trainers. DTD never charges a commission, transaction percentage,
   per-lead fee, or per-introduction fee. Monetisation is exclusively
   trainer-side flat subscriptions and sponsorships.
2. **Acquisition authority:** trainer records may originate only from trainer
   self-submission through `/submit`, self-claim of an existing listing,
   owner-authorised URL submission, or structured ingestion from an explicitly
   approved official/licensed source cross-checked against ABR evidence. Search
   grounding and Places content are not autonomous directory-acquisition feeds.
3. **Legacy-policy retirement:** the old per-introduction policy and
   `founding_profile_prelaunch` copy in `publicPolicy.js` are compatibility
   residue, not alternative commercial models. Remove them when the genuine
   Pro-trial replacement is decided and implemented; do not remove the fallback
   before that decision creates a complete replacement path.
4. **Solo-operator constraint:** DTD is operated by one non-technical founder
   without dedicated engineering or support staff. Prefer low-maintenance,
   low-manual-overhead workflows and surface only meaningful exceptions.

---

## PART 2 — TARGETED POST-LAUNCH STATE

The concrete next evolution of the launched product. Documentation-only —
awaiting explicit implementation authorisation before any of this is
built.

**Already matches target — no change needed, just confirm in docs:**
- Pricing tiers (Free/$19/$39/$199, no $99 tier).
- Diagnostic matching formula remains fit-first; commercial tier is excluded
  from fit scoring and is consulted only inside the five-point comparable-fit
  tiebreak band.
- Refund *logic* (interval-based, already covers Melbourne-Wide).
- Per-suburb sponsor cap (2).

**Implemented locked corrections:**
1. **Per-business suburb cap:** set `SPONSOR_MAX_SUBURBS_PER_TRAINER=4`
   explicitly. The existing 3–5 safety clamp remains; the default is now 4.
2. **Pro trial cohort anchor:** Stripe live mode plus the explicit
   `STRIPE_LIVE_ANCHOR_AT` timestamp is the approved cohort boundary. The
   genuine Pro trial and day-23 warning workflow are implemented; the cohort
   remains intentionally inactive while Stripe uses a test key.
3. **Education route retirement:** approved and implemented. Education is
   separately deployed; main-app legacy routes are redirects only.

**Other targeted-state work (unchanged from earlier planning, now
grounded against real gaps):**
4. **Canonical suburb data:** the approved 539-record asset, idempotent seed
   path, database-first API read, and static fallback are implemented locally.
   The local collection contains 539 active rows and an audit event. Record a
   separate production apply result before claiming the live collection is
   populated.
5. **Indexation infrastructure:** add `listing_count`, `content_word_count`,
   computed `meta_robots`, `gsc_indexed`/`gsc_last_checked` fields per
   suburb; build a real sitemap generator that excludes `noindex` pages;
   fix `/sitemap.xml` and `/robots.txt` to serve actual resources instead
   of the SPA shell (this last part is a plain bug, independent of the
   larger indexation strategy).
6. **Ops tooling — revised from earlier planning:** extend the *existing*
   `/ops` app with a refund/cancel action rather than introducing a new
   tool (Appsmith is no longer the right recommendation now that a
   bespoke action layer already exists). Add MongoDB Atlas Charts
   (still genuinely absent). Fix Sentry so it initialises in the actual
   deployed API process, not only the undeployed worker.
7. **Priority fixes surfaced by the audit:** the First Leash dossier now uses
   a static query-free handoff. Education deployment, domain and PWA verification
   are tracked in the implementation record rather than left as design ambiguity.
   - Clean up legacy/test-like trainer records (`.example.com` stub,
     unstructured-provenance rows) before commercial launch.
8. **Commercial launch itself:** flip Stripe to live mode, set the live anchor
   at the same moment, and enable refund execution only after launch gates pass.

---

## PART 3 — VISIONISED TARGET STATE

Longer-term, not yet prioritised for implementation. Each retains its
original trigger condition from earlier planning; only the ops-layer item
is revised in light of the audit.

- Demand-tiered suburb pricing, once sufficient traffic data exists.
- Active Melbourne-Wide marketing on SEO reach, once ≥50% of the 539
  suburb pages are confirmed indexed and a real sponsor has 60+ days of
  usage data.
- Annual pricing for Suburb/Melbourne-Wide, plus new revenue surfaces
  (trust/verification badge, paid PDF guide pack, Team plan, quarterly
  plan), once subscription volume or a time backstop is reached.
- An automated job that checks the above trigger conditions and notifies
  the operator only when one fires, rather than requiring manual
  dashboard checks.
- ~~Adopt Appsmith as an ops action layer~~ — **retired.** A bespoke
  action layer already exists (`/ops`); future ops evolution extends it
  rather than introducing a parallel tool.

---

## Open items

- Stripe remains in test mode. The approved trial cohort must not activate
  until the live key and `STRIPE_LIVE_ANCHOR_AT` are changed together.
- `DTD_BUILD_INSTRUCTIONS_FOR_AGENTS.md` is absent and must not be described as
  an authority source.
