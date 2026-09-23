# DTD Current State

**Evidence date:** 23 September 2026
**Meaning:** verified descriptive state, not a declaration that the website has reached the owner's intended target.
**Audit scope:** six-part, read-only code/product audit completed 20 September 2026, plus a read-only DNS/hosting reconciliation completed 23 September 2026. It establishes the evidence stated here, not authenticated-operator actions or unexercised production mutations.

## Evidence boundaries

- **Repository evidence:** source, configuration, tests and git state inspected locally.
- **Live evidence:** public API and sites checked read-only on 19–20 September 2026; DNS, Vercel and hosting endpoints rechecked on 23 September 2026.
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
- Legacy education routes redirect to the separate First Leash site. Desktop/mobile primary navigation, the homepage hero/card/footer, and the campaign's education action link directly to First Leash's static root. The unused `POST /api/first-leash` capture model and route have been removed from the main API; the live OpenAPI contract no longer advertises that route.

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
- Before the 23 September 2026 Firebase release, the public host served the SPA shell for `/api/*`, `/sitemap.xml` and `/robots.txt`, while the frontend intentionally called the Cloud Run API directly. The release now routes `/api/*` through Firebase to Cloud Run and serves the static SEO resources with their expected content types; reverify after future hosting or SEO changes.
- First Leash now has Vitest tests and GitHub verification workflows; its old `PROJECT_STATE.md` statement that tests/CI are missing is stale and is corrected by this reconciliation.

## Verification record

- First Leash: TypeScript check and production Vite/PWA build passed; 18 unit tests passed, including print HTML escaping. Local browser checks at 320, 390, 768 and 1440px found no horizontal overflow or page errors. Physical-device print and audio acceptance remains separate.
- Main DTD: 27 frontend tests passed, and its production frontend build passed after the cross-site navigation change.
- Live custom domains served the exact freshly built frontend asset hashes on 19 September 2026 (`main.867ee572.js` for DTD; `index-CDN5-3dC.js` for First Leash after the print-escaping release). On 23 September 2026, the new DTD Firebase release was checked at both the Firebase hostname and `dogtrainersdirectory.com.au`: root HTML, plain-text `robots.txt`, XML `sitemap.xml`, and JSON `/api/health` all returned HTTP 200; the API response reported the database available. Repeatable Chrome and WebKit browser journeys at 390 and 1440px completed DTD navigation → First Leash life-stage and lesson → same-tab, query-free DTD root, without page errors. Both visitor-facing A4 poster PDFs returned HTTP 200 with PDF content type; acoustic play/stop controls, a simulated audio-policy failure/retry path, and isolated dossier print layout passed in both engines. Typed HTML-like dossier text remained text in the live print portal. These checks do not prove physical-device sound output, native print-dialogue appearance, or touch behaviour.
- The main API's education-capture removal passed 266 local backend unit tests (excluding integration tests requiring a local API server). A no-traffic Cloud Run revision was smoke-tested before receiving 100% traffic; live OpenAPI, health, config and trainer reads then passed. An initial all-tests command could not reach a local API. A later isolated run with a live local API and disposable seeded database still returned 292 passed, 12 failures and three errors; see DF-006.
- Main DTD: 25 trial/refund tests passed; 87 public-mode/matching tests passed; 9 focused frontend billing/ops tests passed.
- These checks establish the named contracts only. They do not replace end-to-end production acceptance, provider delivery proof or operator review of authenticated state.

## Open findings discovered during implementation

These entries are verified observations requiring follow-up, not approved product decisions or proof of a comprehensive code audit. Security details are deliberately sanitised because this repository is public.

### DF-001 — Historical Cloud Run source artifact

- **Observed/status:** 19 September 2026 — open.
- **Evidence:** API revision `dtd-api-00015-58d` had a build-source archive containing a local `.env` file, and that historical artifact still exists. A 20 September 2026 read-only inventory found no private-key or service-account files, but found non-empty configuration for database access, `/ops` authentication, trainer-action token signing, ABR, Resend, Google Places, Gemini, Stripe test/unqualified secret keys and webhook verification, and Sentry. Nine archive entries were compared without displaying their values and each matched an enabled Secret Manager version: ABR, admin passcode, MongoDB URL, Places key, Resend key, Sentry DSN, Stripe API key, Stripe webhook secret and trainer-action signing secret. Eight also match the `latest` version injected into the current Cloud Run revision; the archived MongoDB URL matches an older enabled version while the service consumes a different `latest` version. The replacement revision `dtd-api-00016-jid` source archive was checked and does not include `.env`; `backend/.gcloudignore` now excludes it from future source uploads.
- **Risk/uncertainty:** this is active-credential exposure in a historical artifact, not merely stale configuration. The source bucket has no public IAM member, but individual IAM access and historical access remain unresolved; no matching Data Access record was found, and project-level Data Access logging was not configured. This does not establish public exposure or that the file entered the container image.
- **Why deferred:** credential rotation, service reconfiguration and archive disposition are production/security changes requiring an approved, sequenced plan.
- **Next action:** treat all identified archive credentials as compromised; execute an approved provider-by-provider rotation/migration plan, verify each dependent workflow, then separately decide the archive's retention or removal after rollback impact is understood.

### DF-002 — Direct-value secret setting

- **Observed/status:** 19 September 2026 — open.
- **Evidence:** a read-only check of the current `dtd-api` Cloud Run service configuration found `CLOUD_SCHEDULER_SECRET` held as a literal environment value rather than a managed secret reference. The enabled Scheduler job stores the same credential as a literal HTTP header. The Cloud Run service is publicly invokable; this shared credential is the application-level gate for the internal Pro-trial-warning endpoint. No value is recorded here.
- **Dependency verified:** the setting authenticates the enabled daily Pro-trial-warning Scheduler job. Recent Scheduler evidence shows an HTTP 200 response. The live Pro-trial cohort is currently inactive, so the warning processor has no eligible cohort now; the job remains required for the approved trial workflow when that cohort activates. Removing the credential alone would make the endpoint fail closed and break the job.
- **Risk/uncertainty:** principals able to read either service or Scheduler configuration may see the literal value; no unauthorised access has been established. Moving only the Cloud Run value to Secret Manager would leave the Scheduler's duplicate header literal in place, so it is not a complete remedy.
- **Why deferred:** replacing the shared-secret boundary requires a coordinated Scheduler/API authentication design, rotation, and an authenticated end-to-end verification; deleting the integration is not the remedy.
- **Next action:** retain the warning job; implement an approved identity-based Scheduler-to-API authentication path, rotate/remove the shared credential and its duplicate configuration, and verify the next authenticated run before closing.

### DF-003 — Public header does not remain sticky on the live site

- **Observed/status:** 20 September 2026 — open until the paired visual-cohesion candidate is released and checked live.
- **Evidence:** the live directory header moved off-screen during page scroll despite its sticky styling. An `overflow-x: hidden` ancestor prevented the intended sticky behavior. The local frontend candidate replaces this with `overflow-x: clip` on the document ancestors and homepage container; Chrome checks at 320, 390, 768 and 1440px kept the header at the top with no horizontal overflow or page errors. The paired First Leash candidate applies the same correction.
- **Impact/uncertainty:** the live visitor loses primary navigation while scrolling. Local checks do not prove the fix is live or that every browser engine behaves identically.
- **Why deferred:** the 23 September Firebase release included the local visual-cohesion candidate, but the live checks in this session covered routing and content types, not scroll-position/browser visual acceptance.
- **Next action:** release both frontends only after explicit deployment approval, then recheck the scrolling header and cross-site handoff on the live custom domains before closing.
- **Local repair evidence:** the existing DTD candidate now uses `overflow-x: clip` on the document and homepage ancestors rather than a scroll container. On 20 September 2026, local Chromium checks at 1440px and 390px kept the public header at the viewport top after a page scroll, without horizontal overflow or page errors. This does not establish the live Hosting result.

### DF-004 — SEO page creation and indexation eligibility are uncontrolled

- **Observed/status:** 20 September 2026 — open.
- **Evidence:** `GET /api/seo/{slug}` accepts an arbitrary slug. On a cache miss it derives a suburb/category label, calls the AI copy generator, and inserts the result into `seo_pages`; it does not first establish canonical-suburb membership, eligible supply, a configured content threshold, publishing approval, or robots state. The public suburb route requests that endpoint directly. This is in addition to the still-live SPA fallback for `robots.txt` and `sitemap.xml`.
- **Impact/uncertainty:** ordinary crawler or visitor traffic can create stored, AI-authored location pages outside the approved geography/indexation contract. This is a quality, cost, and search-governance risk; the audit did not issue a live arbitrary-slug request, so it did not create or inspect a production record.
- **Why deferred:** correcting it requires a deliberate publishing-state/data migration and hosting-route change, outside this read-only audit.
- **Next action:** make page publication an explicit state derived from the canonical catalogue and eligible-supply/content criteria; serve noindex or 404 for ineligible paths; generate only approved pages; and provide real `robots.txt` and XML sitemap resources before reopening indexation.
- **Local repair status:** `GET /api/seo/{slug}` now rejects non-canonical and nested slugs before any provider call or database write. Canonical pages return a non-indexable, read-only navigation response until both `SEO_MIN_PUBLISHED_TRAINERS` and `SEO_MIN_CONTENT_WORDS` are configured and the locality meets both gates; only then can content be generated and persisted. Static `robots.txt` and a root-only sitemap are present in the frontend build source and were deployed successfully ahead of Firebase's SPA fallback. The backend SEO endpoint repair and any existing-page migration remain unverified in production.
- **Decision required before production indexation:** choose the two numerical threshold values. The active SEO specification requires explicit configuration but deliberately does not set the numbers; absent values now fail closed and prevent new page persistence.

### DF-005 — Public sponsorship claims contradict the approved capacity and matching rules

- **Observed/status:** 20 September 2026 — open.
- **Evidence:** the public pricing page calls Suburb Sponsor an “Exclusive top-slot placement” even though the product contract permits two sponsors per suburb. It also promises Melbourne-Wide is “Featured across diagnostic match results”, while the ranking contract excludes paid status from fit and permits paid preference only as a bounded tie-break among comparable results. The page also promises a sponsor can “change suburb anytime”; the audit found no corresponding self-service contract verification.
- **Impact/uncertainty:** prospective trainers can make paid decisions based on claims that exceed or blur the approved product rules. The audit did not create a subscription or alter sponsor inventory, so it has not verified whether a manual operator process can honour the change request.
- **Why deferred:** this is a public-copy and product-contract correction; changing it during a read-only audit would be an unauthorised product modification.
- **Next action:** align pricing copy, checkout disclosure and tests with two-slot capacity, fit-first matching, and the actual cancellation/change process; explicitly approve any different commercial promise before implementing it.
- **Local repair status:** Pricing now describes one of two sponsored placements, confines sponsor benefit to directory visibility, states that diagnostic matching remains fit-first, and removes the unsupported “change suburb anytime” promise. The copy guard now prevents those retired claims from returning. These frontend changes were included in the 23 September Firebase deployment; public copy review remains separate from endpoint verification.

### DF-006 — Automated delivery gates do not validate the active product end to end

- **Observed/status:** 20 September 2026 — open.
- **Evidence:** the GitHub workflow does not run for direct pushes to `main`, runs only three backend unit files, and performs no frontend test or production build. The repository's prelaunch release-gate script fails because it expects retired public-matching symbols, while the copy-guard script also fails against current public copy. On 20 September 2026, the full backend suite was rerun against a live, isolated local API and disposable seeded database: 292 passed, 12 failed and three errored. The remaining failures assert retired contract details (intro-fee configuration, old oversight fields, endpoint removal, and prior submission outcomes) and assume the startup seed supplies published trainers, whereas the canonical seed creates unclaimed unpublished records. The initial 32 failures/nine errors had also reflected an absent local API; that is not the complete explanation.
- **Impact/uncertainty:** a green CI result or a local broad test command cannot currently establish release readiness for the deployed directory. The 292 passing cases are meaningful evidence for their covered contracts, but the integration suite is partly a historical-contract suite and not a reliable active-product gate.
- **Repair status:** 20 September 2026 — the stale service-test assertions were mapped to the locked commercial, matching, acquisition and operations contracts before replacement. The maintained command is now `python backend/scripts/run_isolated_integration_suite.py`; it starts a local API over a UUID-named loopback-only database, inserts one explicitly verified/published test fixture, disables external providers and removes the database afterwards. It deliberately does not repurpose the cautious canonical intake seed as public test data. The repaired command passed with 310 tests on 20 September 2026. The release-gate and public-copy scripts also passed locally; frontend tests and the production build passed.
- **Remaining gate:** the GitHub workflow now covers direct `main` pushes, the maintained backend command, release scripts, frontend tests and frontend build. It has not yet run in GitHub; the Firebase deployment does not establish the full release gate or complete backend acceptance.

### DF-007 — DNS delegation, frontend hosting and Vercel project ownership are split

- **Observed/status:** 23 September 2026 — open; DNS cutover complete, legacy Vercel cleanup pending.
- **Evidence:** the approved Firebase release added a `/api/**` rewrite to `dtd-api` in `australia-southeast1`, switched the production frontend to same-origin `/api` calls, and deployed successfully. VentraIP DNS Hosting now has the Firebase apex A record (`199.36.158.100`), Firebase `www` CNAME, Firebase `learn` A record, all three Zoho MX records, and the preserved Firebase, Google, Zoho, DMARC, DKIM and SES TXT records. Queries to `ns1`, `ns2` and `ns3.nameserver.net.au` agree; the public apex, `www`, `robots.txt`, `sitemap.xml` and `/api/health` currently return HTTP 200. Public recursive nameserver responses remain mixed while delegation propagates. The legacy Vercel domain attachment and old Vercel `api` route have not yet been removed.
- **Impact/uncertainty:** the canonical Firebase frontend/API path and VentraIP authoritative DNS are aligned. Cached resolvers may still consult Vercel until propagation completes; removing the legacy Vercel attachment or wildcard too early could create an avoidable transition failure.
- **Why deferred:** keep the Vercel legacy attachment and wildcard/API route unchanged until public resolvers consistently show VentraIP nameservers and the domain remains healthy after propagation.
- **Next action:** recheck public resolvers after propagation, then remove the legacy Vercel custom-domain attachment and obsolete wildcard/API route, and verify the public routes again.
