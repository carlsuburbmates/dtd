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

- **Date/status:** 2026-09-18 — locked asset; production seed pending proof.
- **Decision:** the versioned 539-record Australia Post delivery-locality-derived catalogue is the canonical DTD suburb list. It is not derived from trainer records. Database-first API reads may fall back to the same versioned asset.
- **Evidence:** validated asset and seed tool; live `/api/config` count/version/source.
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

- **Date/status:** 2026-09-23 — owner-approved implementation; VentraIP DNS cutover completed, Vercel retirement pending propagation stability.
- **Decision:** Firebase Hosting remains the canonical public frontend; Cloud Run remains the backend; browser API calls use the main domain's `/api/*` path through Firebase Hosting to Cloud Run. DNS management is to move from Vercel DNS to VentraIP, with the required `learn` and mail records preserved and the legacy Vercel domain attachment retired.
- **Evidence:** owner approval in the deployment session; existing Firebase Hosting site and Cloud Run service; local routing change and targeted build validation; VentraIP DNS Hosting now serves the Firebase apex/`www`/`learn` records, Zoho MX records, and preserved verification, DMARC, DKIM and SES TXT records. Authoritative queries to all three VentraIP nameservers agree. Public recursive resolvers are still mixed during nameserver propagation.
- **Rationale:** one public frontend/API origin and one DNS authority reduce stale Vercel routing and CORS/configuration drift for the solo operator.
- **Supersedes:** the split production arrangement in which Vercel DNS delegated the domain while Firebase served the frontend and the frontend bypassed Firebase for Cloud Run.
- **Affected:** `firebase.json`, frontend API base URL, DNS/provider configuration, deployment runbook and current-state evidence.
