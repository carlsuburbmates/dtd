# DTD Current State

**Evidence date:** 24 September 2026
**Meaning:** verified descriptive state, not a declaration that the website has reached the owner's intended target.
**Audit scope:** six-part, read-only code/product audit completed 20 September 2026, plus a read-only DNS/hosting reconciliation completed 23 September 2026. On 24 September, the owner separately authorised guarded Cloud Run recovery, Direct VPC/Cloud NAT rollout, Atlas network restriction, canonical suburb production seeding and one exact invalid-SEO-record cleanup; those production mutations are identified below. Other unexercised operator actions remain outside this evidence.

## Evidence boundaries

- **Repository evidence:** source, configuration, tests and git state inspected locally.
- **Live evidence:** public API and sites checked read-only on 19–20 September 2026; DNS, Vercel and hosting endpoints rechecked on 23 September 2026.
- **Captured operator evidence:** authenticated `/ops` snapshot captured during the preceding implementation audit; refresh before an operational decision.
- A feature is not called live merely because code or a provider integration exists.

## Product and deployment

- The main directory frontend and Cloud Run API are publicly reachable. On 24 September 2026, the API was recovered from a revision blocked by unavailable Sentry configuration, then moved through a zero-traffic Direct VPC canary to `dtd-api-vpc` with 100% traffic. Public health, configuration, trainer-read and Scheduler checks passed before and after the shift; startup logs confirm Sentry initialisation in `production` on the current service.
- The Google Cloud technical migration plan is complete. Firebase Hosting serves the public frontend in project `gen-lang-client-0028123502`; Cloud Run service `dtd-api` in `australia-southeast1` serves the backend; Firebase routes the public `/api/*` path to Cloud Run; and the production domain is managed through VentraIP DNS with Firebase, `learn` and mail records preserved. The public root, `www`, `robots.txt`, `sitemap.xml` and `/api/health` checks passed on 23 September 2026.
- The Google for Startups Cloud Program application remains a separate external review state. The owner-provided Google guidance identified missing public frontend visibility as the review issue; the technical remediation is now complete. No sent support re-review request, Google approval, credits, or support re-review result has been verified or recorded in this repository.
- Public phase is `live_matching`; trainer onboarding and public matching are enabled.
- Stripe webhook handling is enabled, but the Pro-trial cohort is inactive because live mode and its explicit anchor are not both active. Commercial readiness is therefore gated.
- The First Leash is separately built and deployed at `learn.dogtrainersdirectory.com.au`; both sites return HTTP 200.

## Dog-owner workflows

- Directory browsing, filters, trainer profiles and direct protected enquiries are implemented.
- Guided matching calculates trainer fit independently of paid status. A paid-tier preference can reorder only trainers within the five-point comparable-fit band.
- Outcome follow-up, waitlist and notification paths exist, but recent operator evidence includes failed messages and stale loops; unattended operation is not yet accepted.
- Legacy education routes redirect to the separate First Leash site. Desktop/mobile primary navigation, the homepage hero/card/footer, and the campaign's education action link directly to First Leash's static root. The unused `POST /api/first-leash` capture model and route have been removed from the main API; the live OpenAPI contract no longer advertises that route.

## Trainer and billing workflows

- `/submit`, profile status, claim, edit and billing routes exist. Claim verification remains dependent on configured delivery/provider state.
- Implemented products are Free/Core A$0, Pro A$19/month or A$149/year, Suburb Sponsorship A$39/month, and Melbourne-Wide A$199/month. There is no A$99 Regional Sponsor product.
- A real 30-day Stripe Pro trial is implemented for the live-anchor cohort. Stripe owns trial dates; repeat use is prevented; an idempotent day-23 warning workflow exists.
- Suburb sponsorship capacity is two businesses per suburb, with a canonical default of four sponsored suburbs per business. Melbourne-Wide capacity is five.
- Monthly refund eligibility is 14 days and annual Pro eligibility is 30 days. The monthly rule includes Melbourne-Wide. The API refund path is implemented and tested but disabled by its production gate; `/ops` has no refund control.

## Geography and data

- `backend/data/dtd_melbourne_suburbs.v1.json` contains the canonical 539-record Greater Melbourne delivery-locality catalogue and is validated by the seed path.
- On 24 September 2026, the production `suburbs` collection was seeded from canonical SHA-256 `7c45008e4d25d68098d0006f8634ba6259cf1ca19b00cb8a38ef3503efe5d4e1`: the first run created 539 records with no updates or unmanaged records. Live `/api/config` then returned count 539, version `v1`, and source `database`. The second production run reported 539 unchanged, zero created and zero updated. Both production `canonical_suburb_catalogue_seeded` audit events are present.
- The last audited trainer dataset contained a mixture of structured official-source profiles and older records with weak, aggregator, discovery-seed or placeholder provenance. Treat it as launch supply requiring cleanup, not as a uniformly verified corpus.

## Acquisition and ingestion

- Twenty authorised Greater Melbourne profiles were locally built from owner-approved official trainer websites plus ABR identity/status evidence.
- First-party trainer submission is the active growth path.
- Post-launch autonomous acquisition is designed but not production-enabled. It lacks an approved licensed discovery contract, production adapter evidence and an explicit activation decision.
- Gemini may structure a lawfully obtained URL; it is not authority to discover or persist trainer inventory. Google Places/Maps and Search Grounding are excluded as persistent acquisition feeds.

## Operations and observability

- The passcode-gated `/ops` application exposes overview, work queue, supply, messages, billing/reactivation, recent changes, system activity and sponsor inventory.
- `/ops` now includes a protected, sanitised provider-control register. It records runtime configuration presence separately from provider verification, management recovery, safe rotation verification and independent alert-route evidence; it creates review cases rather than overstating any provider as autonomous. It does not expose credential values or make provider calls.
- It reviews and changes case state, but it does not currently provide the full approve/reject/merge/delist/cancel/refund action set promised by old specifications.
- The latest captured authenticated snapshot reported 81 cases, 16 failed messages, 21 open reactivation candidates and stale background loops. These figures are a dated snapshot and must be refreshed before use.
- The unknown PostHog frontend dependency is removed from the current source and production build; this source change has not been deployed in this task, so the live Firebase site remains a separate verification gate. First-party attribution remains in the API for SEO and growth reporting. Sentry now initializes in the deployed API process with the DTD project DSN from the `dtd-sentry-dsn` managed secret; the zero-traffic canary and promoted revision both passed health checks, and Cloud Run startup logs confirmed initialization in `production`. A provider-signed test event and independent alert-route verification remain unexercised. MongoDB Atlas Charts is not integrated.

## SEO and delivery quality

- Suburb routes exist, but production indexation governance is incomplete: there is no authoritative per-suburb listing count/content threshold/robots state/Search Console state pipeline.
- Before the 23 September 2026 Firebase release, the public host served the SPA shell for `/api/*`, `/sitemap.xml` and `/robots.txt`, while the frontend intentionally called the Cloud Run API directly. The release now routes `/api/*` through Firebase to Cloud Run and serves the static SEO resources with their expected content types; reverify after future hosting or SEO changes.
- First Leash now has Vitest tests and GitHub verification workflows; its old `PROJECT_STATE.md` statement that tests/CI are missing is stale and is corrected by this reconciliation.

## Verification record

- First Leash: TypeScript check and production Vite/PWA build passed; 18 unit tests passed, including print HTML escaping. Local browser checks at 320, 390, 768 and 1440px found no horizontal overflow or page errors. Physical-device print and audio acceptance remains separate.
- Main DTD: 27 frontend tests passed, and its production frontend build passed after the cross-site navigation change.
- Live custom domains served the exact freshly built frontend asset hashes on 19 September 2026 (`main.867ee572.js` for DTD; `index-CDN5-3dC.js` for First Leash after the print-escaping release). On 23 September 2026, the new DTD Firebase release was checked at both the Firebase hostname and `dogtrainersdirectory.com.au`: root HTML, plain-text `robots.txt`, XML `sitemap.xml`, and JSON `/api/health` all returned HTTP 200; the API response reported the database available. Repeatable Chrome and WebKit browser journeys at 390 and 1440px completed DTD navigation → First Leash life-stage and lesson → same-tab, query-free DTD root, without page errors. Both visitor-facing A4 poster PDFs returned HTTP 200 with PDF content type; acoustic play/stop controls, a simulated audio-policy failure/retry path, and isolated dossier print layout passed in both engines. Typed HTML-like dossier text remained text in the live print portal. These checks do not prove physical-device sound output, native print-dialogue appearance, or touch behaviour.
- The main API's education-capture removal passed 266 local backend unit tests (excluding integration tests requiring a local API server). A no-traffic Cloud Run revision was smoke-tested before receiving 100% traffic; live OpenAPI, health, config and trainer reads then passed. The maintained isolated suite was rerun on 24 September with a live local API and disposable seeded database: 313 tests passed (with four FastAPI deprecation warnings); see DF-006.
- Main DTD: 25 trial/refund tests passed; 87 public-mode/matching tests passed; 9 focused frontend billing/ops tests passed.
- These checks establish the named contracts only. They do not replace end-to-end production acceptance, provider delivery proof or operator review of authenticated state.

## Open findings discovered during implementation

These entries are verified observations requiring follow-up, not approved product decisions or proof of a comprehensive code audit. Security details are deliberately sanitised because this repository is public.

### DF-001 — Historical Cloud Run source artifact

- **Observed/status:** 24 September 2026 — partially remediated; archive retained pending external-provider rotation.
- **Evidence:** API revision `dtd-api-00015-58d` had a build-source archive containing a local `.env` file, and that historical artifact still exists. The replacement source archive excludes `.env` through `backend/.gcloudignore`. The previously direct Scheduler credential and duplicate Scheduler header were replaced with a dedicated service-account OIDC token checked at the warning endpoint; the live scheduled run returned HTTP 200 after the strict route-level check was deployed. The `/ops` passcode and trainer-action token secret were replaced with version 2 and version 1 disabled. The retired Places key and its Secret Manager entry were revoked/removed. The archive's Gemini key was matched in memory to an unused First Leash-labelled Google API-key resource, then revoked; First Leash had no source/build reference to it and its unused local `.env` was removed. No credential material is recorded here.
- **Risk/uncertainty:** this remains credential exposure in a historical artifact. The source bucket has no public IAM member, but individual IAM access and historical access remain unresolved; no matching Data Access record was found, and project-level Data Access logging was not configured. This does not establish public exposure or that the file entered a container image. Sanitised reporting and completed rotations do not establish that no exposure occurred.
- **Remaining rotation scope (identity/scope only):** MongoDB URL/database user (Atlas access), Resend API key (transactional email), Sentry DSN (event ingestion), Stripe API/webhook credentials (billing and webhook authenticity), and the archive's Stripe test secret require their respective provider-management surfaces. Existing trainer/billing action links signed before the replacement action-token secret are intentionally invalidated.
- **ABR GUID ownership:** The ABR GUID is a one-time government-issued runtime identifier, not a rotating application credential. Cloud Run receives it through Secret Manager; if it is lost or invalid, recovery follows the Australian Government's ABR process rather than an application rotation workflow.
- **24 September authenticated-console inventory and network remediation:** Resend has two full-access keys rather than a least-privilege sending key. Atlas has one broad database user, one retained home-recovery `/32`, and Cloud Run's fixed Direct VPC egress `/32`; the unrestricted `0.0.0.0/0` entry retained from the earlier Render deployment was removed after the new address became active. Cloud Run's zero-traffic canary, overlapping allow-list check and post-removal public health/config/trainer checks all passed; Cloud Run logged no error events in the following ten-minute observation window. A direct client from this Mac no longer connected after the broad rule's removal, so the retained home-recovery entry must **not** be treated as proven recovery access until it is independently tested and, if needed, refreshed through a controlled recovery procedure. Stripe has a live webhook destination at the retired Render API rather than the current Cloud Run API; the current Cloud Run webhook route is reachable but has not received a provider-signed delivery. Sentry now initialises from enabled managed-secret version 2; a provider-signed test event and independent alert-route verification remain unexercised. The Cloud Run runtime service account's former project-wide Secret Manager accessor role was replaced with resource-level access to exactly its eight then-mounted runtime secrets; the resulting revision passed the live health check. No credential value, provider mutation, or customer/billing action is recorded here.
- **Risk/uncertainty:** the Atlas network perimeter is now restricted to explicit entries, but its database identity remains broader than needed and the local recovery route is unverified. The retired Stripe destination means current billing-webhook delivery is not established. The Stripe account's visible setup state also means commercial activation remains separately gated; this inventory did not charge, refund, or contact any customer.
- **Why deferred:** replacing the Atlas database identity and validating a device-independent recovery route require a replacement credential and Secret Manager cutover, which must be created, verified and observed before revocation. Provider credential replacement must create and verify a replacement before revocation; archive deletion/retention is a later decision, not a substitute for rotation.
- **Next action:** create a least-privilege Atlas database user, place its replacement connection credential in Secret Manager, validate a successor Cloud Run revision, then retire the broad user after an observation window. Establish and test a separate provider-management recovery route that does not depend on this Mac. Separately, create least-privilege replacement credentials, update Secret Manager and the Stripe webhook destination, verify each dependent flow, then revoke old credentials after an observation window. Enable appropriate Data Access logging before treating historical-access investigation as complete.

### DF-003 — Public header does not remain sticky on the live site

- **Observed/status:** 20 September 2026 — open until the paired visual-cohesion candidate is released and checked live.
- **Evidence:** the live directory header moved off-screen during page scroll despite its sticky styling. An `overflow-x: hidden` ancestor prevented the intended sticky behavior. The local frontend candidate replaces this with `overflow-x: clip` on the document ancestors and homepage container; Chrome checks at 320, 390, 768 and 1440px kept the header at the top with no horizontal overflow or page errors. The paired First Leash candidate applies the same correction.
- **Impact/uncertainty:** the live visitor loses primary navigation while scrolling. Local checks do not prove the fix is live or that every browser engine behaves identically.
- **Why deferred:** the 23 September Firebase release included the local visual-cohesion candidate, but the live checks in this session covered routing and content types, not scroll-position/browser visual acceptance.
- **Next action:** release both frontends only after explicit deployment approval, then recheck the scrolling header and cross-site handoff on the live custom domains before closing.
- **Local repair evidence:** the existing DTD candidate now uses `overflow-x: clip` on the document and homepage ancestors rather than a scroll container. On 20 September 2026, local Chromium checks at 1440px and 390px kept the public header at the viewport top after a page scroll, without horizontal overflow or page errors. This does not establish the live Hosting result.

### DF-004 — SEO page creation and indexation eligibility are controlled for new pages; legacy-page review remains

- **Observed/status:** 24 September 2026 — production repair deployed and verified for new non-canonical requests. Existing canonical-page eligibility has not yet been retroactively inventoried.
- **Prior evidence:** before the repair, `GET /api/seo/{slug}` accepted arbitrary slugs and, on a cache miss, could derive a label, call the AI copy generator and insert a record into `seo_pages` without first establishing canonical membership or publication eligibility.
- **Production repair evidence:** Cloud Run revision `dtd-api-00019-cip` received 100% traffic after a zero-traffic tagged smoke test. It has `SEO_MIN_PUBLISHED_TRAINERS=3` and `SEO_MIN_CONTENT_WORDS=500` configured. Both its candidate URL and the public Firebase-routed `/api/seo/` path returned HTTP 404 with `Unknown canonical suburb` for a non-canonical slug; the request did not invoke generation or create a record. One invalid record created by the earlier pre-repair audit request was identified by its exact database identifier, deleted as an authorised cleanup, and confirmed absent. No broader `seo_pages` migration was performed.
- **Current contract:** `GET /api/seo/{slug}` rejects non-canonical and nested slugs before any provider call or database write. Canonical pages return a non-indexable, read-only navigation response until both configured thresholds are met; only then can content be generated and persisted. Static `robots.txt` and a root-only sitemap are served by Firebase ahead of SPA fallback.
- **Residual risk/next gate:** an existing canonical `seo_pages` record can still be returned before its current supply/content eligibility is re-evaluated. Before reopening indexation, inventory those existing records and explicitly approve any migration, noindex or deletion action; do not infer that the targeted invalid-record cleanup proved the legacy corpus compliant.
- **Threshold decision:** 24 September 2026 — the owner approved three eligible published trainers and 500 content words as adjustable starting thresholds. They are now configured on the deployed API revision.

### DF-005 — Public sponsorship claims contradict the approved capacity and matching rules

- **Observed/status:** 20 September 2026 — open.
- **Evidence:** the public pricing page calls Suburb Sponsor an “Exclusive top-slot placement” even though the product contract permits two sponsors per suburb. It also promises Melbourne-Wide is “Featured across diagnostic match results”, while the ranking contract excludes paid status from fit and permits paid preference only as a bounded tie-break among comparable results. The page also promises a sponsor can “change suburb anytime”; the audit found no corresponding self-service contract verification.
- **Impact/uncertainty:** prospective trainers can make paid decisions based on claims that exceed or blur the approved product rules. The audit did not create a subscription or alter sponsor inventory, so it has not verified whether a manual operator process can honour the change request.
- **Why deferred:** this is a public-copy and product-contract correction; changing it during a read-only audit would be an unauthorised product modification.
- **Next action:** release only after the final commercial gate verifies the exact UI → checkout API → Stripe → webhook → entitlement/inventory → notification/fallback → `/ops` sequence without creating an unintended charge.
- **Local repair status:** Pricing now describes one of two sponsored placements, confines sponsor benefit to directory visibility, states that diagnostic matching remains fit-first, and removes unsupported “change suburb anytime”, click-tracking, onboarding-support and cross-suburb-capability claims. The checkout API now distinguishes monthly and annual Pro idempotency keys, requires a persisted versioned acceptance of the public terms, and fails closed until the explicit new-checkout gate is enabled. `past_due` remains an `/ops` recovery case while Stripe retries; terminal `unpaid` and `incomplete_expired` states remove paid entitlement and release sponsorship inventory. These local changes are not yet deployed or live-commercial acceptance evidence.

### DF-006 — Automated delivery gates do not validate the active product end to end

- **Observed/status:** 20 September 2026 — open.
- **Evidence:** the GitHub workflow does not run for direct pushes to `main`, runs only three backend unit files, and performs no frontend test or production build. The repository's prelaunch release-gate script fails because it expects retired public-matching symbols, while the copy-guard script also fails against current public copy. On 20 September 2026, the full backend suite was rerun against a live, isolated local API and disposable seeded database: 292 passed, 12 failed and three errored. The remaining failures assert retired contract details (intro-fee configuration, old oversight fields, endpoint removal, and prior submission outcomes) and assume the startup seed supplies published trainers, whereas the canonical seed creates unclaimed unpublished records. The initial 32 failures/nine errors had also reflected an absent local API; that is not the complete explanation.
- **Impact/uncertainty:** a green CI result or a local broad test command cannot currently establish release readiness for the deployed directory. The 292 passing cases are meaningful evidence for their covered contracts, but the integration suite is partly a historical-contract suite and not a reliable active-product gate.
- **Repair status:** 20 September 2026 — the stale service-test assertions were mapped to the locked commercial, matching, acquisition and operations contracts before replacement. The maintained command is now `python backend/scripts/run_isolated_integration_suite.py`; it starts a local API over a UUID-named loopback-only database, inserts one explicitly verified/published test fixture, disables external providers and removes the database afterwards. It deliberately does not repurpose the cautious canonical intake seed as public test data. The maintained suite passed with 313 tests on 24 September 2026 (four FastAPI deprecation warnings). The release-gate and public-copy scripts also passed locally; frontend tests and the production build passed.
- **Remaining gate:** the GitHub workflow now covers direct `main` pushes, the maintained backend command, release scripts, frontend tests and frontend build. It has not yet run in GitHub; the Firebase deployment does not establish the full release gate or complete backend acceptance.

### DF-007 — DNS delegation and legacy Vercel ownership

- **Observed/status:** 24 September 2026 — remediated.
- **Evidence:** Firebase Hosting routes `/api/**` to `dtd-api` in `australia-southeast1`, while VentraIP is authoritative for the Firebase apex, `www`, `learn` and retained mail records. All three independent public resolvers returned the VentraIP nameservers and Firebase apex record. The legacy Vercel root-domain attachment (including its attached `www` alias) was then removed from the exact legacy Vercel project; its obsolete catch-all SPA configuration was removed from the repository. The public root, `robots.txt`, `sitemap.xml` and `/api/health` each returned HTTP 200 immediately after removal.
- **Residual uncertainty:** the legacy Vercel project itself was deliberately retained because it may contain deployment history; it no longer owns this domain. This check establishes the public routing contract, not a complete Vercel-account audit.
