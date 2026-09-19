# DTD Current State

**Evidence date:** 19 September 2026
**Meaning:** verified descriptive state, not a declaration that the website has reached the owner's intended target.

## Evidence boundaries

- **Repository evidence:** source, configuration, tests and git state inspected locally.
- **Live evidence:** public API and sites checked read-only on 19 September 2026.
- **Captured operator evidence:** authenticated `/ops` snapshot captured during the preceding implementation audit; refresh before an operational decision.
- A feature is not called live merely because code or a provider integration exists.

## Product and deployment

- The main directory frontend and Cloud Run API are publicly reachable. The API health response reports the database available.
- Public phase is `live_matching`; trainer onboarding and public matching are enabled.
- Stripe webhook handling is enabled, but the Pro-trial cohort is inactive because live mode and its explicit anchor are not both active. Commercial readiness is therefore gated.
- The First Leash is separately built and deployed at `learn.dogtrainersdirectory.com.au`; both sites return HTTP 200.

## Dog-owner workflows

- Directory browsing, filters, trainer profiles and direct protected enquiries are implemented.
- Guided matching calculates trainer fit independently of paid status. A paid-tier preference can reorder only trainers within the five-point comparable-fit band.
- Outcome follow-up, waitlist and notification paths exist, but recent operator evidence includes failed messages and stale loops; unattended operation is not yet accepted.
- Legacy education routes redirect to the separate First Leash site. The main repository still contains an unused `POST /api/first-leash` model/endpoint and stale campaign education copy, so code separation is incomplete.

## Trainer and billing workflows

- `/submit`, profile status, claim, edit and billing routes exist. Claim verification remains dependent on configured delivery/provider state.
- Implemented products are Free/Core A$0, Pro A$19/month or A$149/year, Suburb Sponsorship A$39/month, and Melbourne-Wide A$199/month. There is no A$99 Regional Sponsor product.
- A real 30-day Stripe Pro trial is implemented for the live-anchor cohort. Stripe owns trial dates; repeat use is prevented; an idempotent day-23 warning workflow exists.
- Suburb sponsorship capacity is two businesses per suburb, with a canonical default of four sponsored suburbs per business. Melbourne-Wide capacity is five.
- Monthly refund eligibility is 14 days and annual Pro eligibility is 30 days. The monthly rule includes Melbourne-Wide. The API refund path is implemented and tested but disabled by its production gate; `/ops` has no refund control.

## Geography and data

- `backend/data/dtd_melbourne_suburbs.v1.json` contains the canonical 539-record Greater Melbourne delivery-locality catalogue and is validated by the seed path.
- `/api/config` returned 539 suburbs and version `v1` on 19 September 2026, with source `static_catalogue_fallback`. This proves public coverage but does **not** prove the production `suburbs` collection has been seeded exactly.
- Local idempotent seeding was completed. Production database application remains unproven.
- The last audited trainer dataset contained a mixture of structured official-source profiles and older records with weak, aggregator, discovery-seed or placeholder provenance. Treat it as launch supply requiring cleanup, not as a uniformly verified corpus.

## Acquisition and ingestion

- Twenty authorised Greater Melbourne profiles were locally built from owner-approved official trainer websites plus ABR identity/status evidence.
- First-party trainer submission is the active growth path.
- Post-launch autonomous acquisition is designed but not production-enabled. It lacks an approved licensed discovery contract, production adapter evidence and an explicit activation decision.
- Gemini may structure a lawfully obtained URL; it is not authority to discover or persist trainer inventory. Google Places/Maps and Search Grounding are excluded as persistent acquisition feeds.

## Operations and observability

- The passcode-gated `/ops` application exposes overview, work queue, supply, messages, billing/reactivation, recent changes, system activity and sponsor inventory.
- It reviews and changes case state, but it does not currently provide the full approve/reject/merge/delist/cancel/refund action set promised by old specifications.
- The latest captured authenticated snapshot reported 81 cases, 16 failed messages, 21 open reactivation candidates and stale background loops. These figures are a dated snapshot and must be refreshed before use.
- PostHog is wired in the public frontend. Sentry configuration exists but was not initialising in the deployed API path at the last audit. MongoDB Atlas Charts is not integrated.

## SEO and delivery quality

- Suburb routes exist, but production indexation governance is incomplete: there is no authoritative per-suburb listing count/content threshold/robots state/Search Console state pipeline.
- The public host currently serves the SPA shell for `/api/*`; the frontend intentionally calls the Cloud Run API directly. API health must therefore be checked at the configured Cloud Run origin, not inferred from the Firebase host.
- Earlier audit evidence found `/sitemap.xml` and `/robots.txt` resolving incorrectly through the SPA fallback. Reverify after any hosting or SEO change.
- First Leash now has Vitest tests and GitHub verification workflows; its old `PROJECT_STATE.md` statement that tests/CI are missing is stale and is corrected by this reconciliation.

## Verification record

- First Leash: TypeScript check passed; 15 tests passed; production Vite/PWA build passed.
- Main DTD: 25 trial/refund tests passed; 87 public-mode/matching tests passed; 9 focused frontend billing/ops tests passed.
- These checks establish the named contracts only. They do not replace end-to-end production acceptance, provider delivery proof or operator review of authenticated state.
