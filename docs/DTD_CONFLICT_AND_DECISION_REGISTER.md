# DTD Conflict and Decision Register

**Schema:** each decision records date, status, evidence, rationale, superseded statements and affected documents. “Locked” means it remains authoritative until explicitly superseded here.

## CDR-001 — Education is separately deployed

- **Date/status:** 2026-09-18 — locked.
- **Decision:** The First Leash is the sole education application at `learn.dogtrainersdirectory.com.au`. DTD uses branded links and redirects; cross-site URLs carry no dossier or behavioural data.
- **Evidence:** explicit owner approval; separate repository/deployment; bridge unit test; live HTTP response.
- **Rationale:** clear ownership, independent delivery and privacy-safe handoff.
- **Supersedes:** integrated `/learn` proposals and duplicated main-repository education/API content.
- **Affected:** invariants; current/target state; First Leash `DTD_INTEGRATION.md`.

## CDR-002 — Canonical commercial products

- **Date/status:** 2026-09-18 — locked.
- **Decision:** Free/Core A$0; Pro A$19/month or A$149/year; Suburb Sponsorship A$39/month; Melbourne-Wide A$199/month. No A$99 Regional Sponsor tier.
- **Evidence:** explicit owner approval; pricing UI; Stripe plan mapping; billing tests.
- **Rationale:** one simple flat-subscription model without a phantom ranking tier.
- **Supersedes:** master-matrix Regional Sponsor references and inactive legacy offer copy.
- **Affected:** monetisation and matching specs; public pricing; billing.

## CDR-003 — Pro trial cohort anchor

- **Date/status:** 2026-09-18 — locked and implemented; production cohort inactive.
- **Decision:** first-time eligible Pro subscribers receive 30 days. Cohort eligibility begins only when Stripe live mode and `STRIPE_LIVE_ANCHOR_AT` are active; Stripe subscription creation starts the actual trial. Warning is due on day 23 and is idempotent.
- **Evidence:** explicit owner approval; provider-backed implementation and focused tests.
- **Rationale:** prevents a commercially meaningless pre-live cohort and ties dates to provider truth.
- **Supersedes:** unsupported “Stage 3/weeks 3–4” language and any launch-date inference.
- **Affected:** monetisation and ops specs; runtime configuration.

## CDR-004 — Sponsorship caps

- **Date/status:** 2026-09-18 — locked and implemented.
- **Decision:** two active sponsors per suburb; default maximum four sponsored suburbs per business; five Melbourne-Wide positions. The environment value may remain clamped from three through five, but four is the canonical setting.
- **Evidence:** explicit owner approval; inventory service and tests.
- **Rationale:** finite scarcity without allowing one business to monopolise local inventory.
- **Supersedes:** “3 to 5 suburbs” as a policy and historical five-suburb statements.
- **Affected:** monetisation and geography specs; inventory configuration.

## CDR-005 — Paid status and diagnostic matching

- **Date/status:** 2026-09-18 — locked and implemented.
- **Decision:** paid status contributes zero to diagnostic fit. Tier weight can break order only among trainers within 0.05 (five percentage points) of the top fit score.
- **Evidence:** explicit owner approval; matching implementation; 87 focused public-mode/scoring tests.
- **Rationale:** recommendations remain suitability-led while giving a bounded, transparent sponsorship benefit among comparable options.
- **Supersedes:** the 15% Pro Verification fit weight and unrestricted paid-first diagnostic ranking.
- **Affected:** matching spec; AI prompt; deterministic ranking.

## CDR-006 — Melbourne-Wide refund treatment

- **Date/status:** 2026-09-18 — locked contract; execution gated.
- **Decision:** interval-based eligibility applies to the product: 14 days for monthly plans, including Melbourne-Wide, and 30 days for annual Pro. ACL rights remain additional. Production refund execution stays disabled until operator, audit and live-payment gates pass.
- **Evidence:** owner approval; backend refund path and focused tests.
- **Rationale:** one consistent plan-interval rule with fail-closed financial operations.
- **Supersedes:** omission of Melbourne-Wide from named refund examples and claims that one-click `/ops` refunds are already live.
- **Affected:** monetisation and ops specs; billing UI/API.

## CDR-007 — Canonical Greater Melbourne catalogue

- **Date/status:** 2026-09-18 — locked asset; production seed verified 2026-09-24.
- **Decision:** the versioned 539-record Australia Post delivery-locality-derived catalogue is the canonical DTD suburb list. It is not derived from trainer records. Database-first API reads may fall back to the same versioned asset.
- **Evidence:** validated asset and seed tool; live `/api/config` count/version/source. On 2026-09-24, the Cloud Run production connection dry-run found zero existing `suburbs` records and an exact plan to create 539 canonical records from SHA-256 `7c45008e4d25d68098d0006f8634ba6259cf1ca19b00cb8a38ef3503efe5d4e1`; no rows would be updated or preserved. The authorised first production run then created exactly 539 records, and the live API changed from `static_catalogue_fallback` to `database`. The required second production run reported 539 unchanged with zero created or updated. Both seed audit events are present.
- **Rationale:** stable geography independent of current directory supply.
- **Supersedes:** approximate 300-suburb claims and dynamic extraction from 20 trainer rows.
- **Affected:** geography and SEO specs; `/api/config`; production seed.

## CDR-008 — Acquisition authority

- **Date/status:** 2026-09-11 — locked; evidence amended 2026-09-20.
- **Decision:** use first-party submission/claim, owner-authorised official sites, or approved licensed feeds; ABR verifies identity; Gemini URL extraction can structure authorised content. Search Grounding, Places/Maps and generic scraping are excluded from persistent acquisition.
- **Evidence:** owner-approved pipeline, implemented scripts and source manifests. On 2026-09-20, a separate reviewer independently checked Google's primary terms pages: Google Maps Platform Terms §3.2.3 says “copy and save business names, addresses, or user reviews”; Gemini API Additional Terms says “it is a violation of these terms to use Grounding with Google Search to extract or collect one or more of these components for another purpose” and separately prohibits storing or link-tracking Grounded Results/Search Suggestions outside stated exceptions. This confirms the existing prohibition against using Places/Maps or Gemini Search Grounding for DTD's persistent discovery/acquisition pipeline.
- **Rationale:** lawful, reproducible supply growth with correction and suppression rights.
- **Supersedes:** AI/search-as-database proposals.
- **Affected:** acquisition spec and invariants.

## CDR-009 — Solo-operator action layer

- **Date/status:** 2026-09-18 — locked direction.
- **Decision:** extend and simplify the existing `/ops` application; do not add Appsmith as a parallel operator tool. Expose only real, bounded and auditable actions.
- **Evidence:** explicit architecture approval; existing `/ops` implementation.
- **Rationale:** lower maintenance and one source of operational truth.
- **Supersedes:** Appsmith recommendation and old one-click action claims not supported by UI.
- **Affected:** ops spec and targeted state.

## CDR-010 — Documentation architecture

- **Date/status:** 2026-09-19 — locked.
- **Decision:** active main-repository product authority is README, four state/governance documents and six topic specs. README is both map and owner-readable synthesis but creates no facts. First Leash keeps its own documentation and integration contract.
- **Evidence:** owner-approved six-plus-six architecture and README amendment.
- **Rationale:** small, navigable authority set with contradictions detectable by topic.
- **Supersedes:** monolithic master/canonical documents and active reconciliation prompts/status logs.
- **Affected:** both repositories' documentation trees.

## CDR-011 — Licensed discovery-source outreach outcome

- **Date/status:** 2026-09-20 — current sourcing outcome; review if a new written licence becomes available.
- **Decision:** no licensed automated discovery feed is currently available or pursued. First-party submission/claim, owner-authorised official URLs and bounded manual curation remain DTD's active acquisition channels under CDR-008 and the acquisition invariant.
- **Evidence:** Thryv Data, operator of the former Sensis Business Search API, replied on 11 September 2026 that SAPI is no longer available and business data is no longer sold. Google's Programmable Search Products team replied on 16 September 2026 with (a) a general web-search API priced at US$15 CPM with a US$30,000/month minimum and (b) Vertex AI Grounded Generation for search over known domains, not discovery of unknown businesses. Neither product was pursued; the latter would also conflict with CDR-008's confirmed Grounding restriction. Thryv's referral to `smrtr.com.au` has not yet been vetted and remains one low-effort outreach lead.
- **Rationale:** the outreach closes two investigated paths without pretending a compliant, affordable alternative exists. It preserves the lawful manual baseline rather than creating pressure to use prohibited Google-derived discovery.
- **Supersedes:** the undetermined Sensis/Thryv SAPI candidate state and any implication that Google search products are an approved DTD discovery feed.
- **Affected:** acquisition specification, source-outreach backlog and future vendor evaluation.

## CDR-012 — Production web routing ownership

- **Date/status:** 2026-09-24 — owner-approved implementation; Google Cloud technical migration and VentraIP DNS cutover completed; legacy Vercel domain ownership and obsolete catch-all configuration retired after public resolver verification.
- **Decision:** Firebase Hosting remains the canonical public frontend; Cloud Run remains the backend; browser API calls use the main domain's `/api/*` path through Firebase Hosting to Cloud Run. VentraIP is the DNS authority, with the required `learn` and mail records preserved. The legacy Vercel domain attachment and wildcard/API route are retired only after public DNS propagation is stable.
- **Evidence:** owner approval in the deployment session; existing Firebase Hosting site and Cloud Run service; local routing change and targeted build validation; VentraIP DNS Hosting now serves the Firebase apex/`www`/`learn` records, Zoho MX records, and preserved domain-verification, DMARC and DKIM records. Authoritative queries to all three VentraIP nameservers agree. Public recursive resolvers are still mixed during nameserver propagation.
- **Rationale:** one public frontend/API origin and one DNS authority reduce stale Vercel routing and CORS/configuration drift for the solo operator. The Vercel removal followed independent resolver and public-route verification.
- **Supersedes:** the split production arrangement in which Vercel DNS delegated the domain while Firebase served the frontend and the frontend bypassed Firebase for Cloud Run.
- **Affected:** `firebase.json`, frontend API base URL, DNS/provider configuration, deployment runbook and current-state evidence.

## CDR-013 — SEO publication thresholds

- **Date/status:** 2026-09-24 — locked starting configuration; review with real publishing and traffic evidence.
- **Decision:** an SEO suburb page is eligible for generation and indexation only when it has at least three eligible published trainers and generated content of at least 500 words. The thresholds are explicit environment configuration, not page-copy promises or an inference from the 539-record catalogue.
- **Evidence:** explicit owner approval; the existing SEO/indexation contract requires configuration-based supply and quality gates.
- **Rationale:** this gives the fail-closed implementation a concrete, adjustable starting point without treating an empty locality or thin generated copy as indexable.
- **Supersedes:** the unresolved numerical-threshold state in DF-004 and the blank values in the environment template.
- **Affected:** SEO/indexation specification, runtime environment configuration, tests and release verification.

## CDR-014 — Google for Startups technical migration completion

- **Date/status:** 2026-09-24 — technical migration complete; Google program re-review pending.
- **Decision:** Treat the Google Cloud remediation plan as complete for the technical deployment scope: Firebase Hosting provides the public frontend in project `gen-lang-client-0028123502`, Cloud Run provides `dtd-api`, Firebase proxies `/api/*` to Cloud Run, and the domain's VentraIP DNS preserves the Firebase, `learn` and mail records. Do not represent the Google for Startups application as approved until Google provides written confirmation.
- **Evidence:** owner-provided Google Cloud Startup guidance; successful Firebase deployment; public HTTP 200 checks for the root, `www`, `robots.txt`, `sitemap.xml` and `/api/health`; authoritative VentraIP queries for apex, `www`, `learn`, Zoho MX, domain-verification, DMARC and DKIM records; commit `e4e8406`.
- **Rationale:** the previously identified public-frontend visibility gap has been remediated while keeping external program approval separate from repository and deployment evidence.
- **Supersedes:** the earlier technical migration state in which Cloud Run existed but the public frontend and routing were not sufficiently aligned for manual Google review.
- **Affected:** Google Startup review response, deployment/current-state evidence and production handover.

## CDR-015 — Sentry project identity and runtime connection

- **Date/status:** 2026-09-24 — implemented and reconciled; autonomous alerting remains unaccepted.
- **Decision:** Use Sentry organisation `dtd-i9` project `dtd` as the repository's single application-error project. Remove the obsolete `barkbond-web` and `javascript-nextjs` projects. Keep the deployed API connection on the managed DTD DSN and initialise Sentry in the process serving production requests.
- **Evidence:** authenticated Sentry project inventory; project rename/platform update; deletion responses for the two obsolete projects; managed Secret Manager version 2; zero-traffic Cloud Run verification, promoted revision health check and production startup log.
- **Rationale:** one repository, one named Sentry project and one deployed runtime path reduce identity drift without exposing provider credentials in source or documentation.
- **Supersedes:** the earlier BarkBond-labelled project arrangement and the worker-only Sentry initialisation path.
- **Affected:** Sentry provider configuration, API startup, worker startup, environment templates and current-state evidence.

## CDR-016 — Google Cloud billing and owner-access reconciliation

- **Date/status:** 2026-09-24 — reconciled; no further IAM or billing change authorised.
- **Decision:** Keep project `gen-lang-client-0028123502` linked to billing account `0104B3-AB5AF0-8F0A01` under the `dogtrainersdirectory.com.au` organisation. Retain the existing project Owner access for the owner's personal identity because this is a one-owner project; do not change project IAM or billing administration as part of this work.
- **Evidence:** Cloud Console billing-management view under the work organisation context; local project and billing-link inspection; no billing or IAM mutation was performed during reconciliation.
- **Rationale:** the billing relationship is already aligned with the work organisation, and the retained owner access reflects the owner's explicit operating choice. The repository records the relationship without recording account credentials or private console URLs.
- **Supersedes:** uncertainty about whether the current project was attached to a personal billing account.
- **Affected:** current-state evidence and future Google Cloud access reconciliation.
