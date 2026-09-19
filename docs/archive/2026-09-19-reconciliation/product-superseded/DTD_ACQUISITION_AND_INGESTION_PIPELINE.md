# DTD Acquisition And Ingestion Pipeline

**Status:** Canonical source and data-use boundary  
**Last verified:** 2026-09-11  
**Scope:** Initial launch supply and post-launch trainer acquisition for Greater Melbourne

## 1. Purpose

This document is the source of truth for how DTD discovers, verifies, enriches,
publishes, refreshes, and suppresses trainer listings. It supersedes any older
statement that Google Places, Google Maps data, Gemini Search Grounding, an
unlicensed search result, or AI confidence alone may populate the persistent
trainer directory.

The operating goal is low-touch acquisition for a solo owner without weakening
source rights, evidence, quality, trainer control, or delisting protection.

## 2. Current Truth

| Item | State | What it means |
| --- | --- | --- |
| Initial launch supply | Accepted locally | 20 authorised Greater Melbourne profiles were built from approved official trainer websites and active ABR identity/status evidence. |
| Trainer submissions and claims | Implemented | Trainers may submit, claim, correct, enrich, or request removal of profiles through DTD's first-party workflows. |
| ABR Web Services | Approved for bounded uses | ABR is used for ABN/name identity and active-status verification, not website or category discovery. |
| Official trainer websites | Approved with controls | Only public business facts may be extracted, with source evidence, robots/site-term checks, `DTD-Bot/1.0`, and at most one request per two seconds per domain. |
| Sensis/Thryv discovery feed | Supplier enquiry sent | Formal pilot inquiry (100–500 listings) sent to `dataenquiry@thryv.com`. SAPI brochure confirms publishing use case. Awaiting commercial terms, schema, and contract. |
| Google Web Search Products | Inquiry submitted | Official request submitted via Web Search Products interest form following Custom Search API deprecation; awaiting response on permissible URL discovery. |
| Manual trainer registration (`/submit`) | Active primary growth CTA | Primary post-launch inventory driver while third-party commercial agreements are pending. All submissions pass statutory ABR and quality gates. |
| MacroMatch and TotalCheck | Not a discovery source | Current public material describes validation, cleansing, and enrichment of records already held. These products may be considered later only for an approved validation use. |
| Google Places/Maps content | Excluded from persistent acquisition | A configured key does not permit DTD to copy or persist names, addresses, phones, reviews, ratings, photos, or other Places content as directory inventory. |
| Gemini Search Grounding | Excluded from acquisition | It must not collect links, build an index, or identify pages for automated crawling or scraping. |
| Gemini URL-based extraction | Conditional enrichment only | Gemini may structure factual content from a URL that DTD already obtained lawfully, subject to the source's terms, Google terms, privacy controls, schema validation, and deterministic fallback. |
| Post-launch acquisition automation | Designed, not production-enabled | It awaits an approved licensed discovery contract, an implemented adapter, dry-run evidence, authenticated scheduling, and explicit activation. |

## 3. One Pipeline, Two Operating Modes

DTD uses one governed pipeline. It does not create a separate post-launch
scraper.

### Mode A: launch baseline

`owner-approved official website URL -> bounded factual capture -> ABR check -> canonicalise/dedupe/suppress -> quality gate -> authorised publish or hold -> /ops evidence`

The accepted 20-profile launch batch is reproducible through:

- `scripts/build_initial_trainer_batch.py`
- `backend/data/melbourne_trainers_seed.json`
- `backend/data/initial_trainer_batch_dry_run_manifest.json`
- `backend/data/initial_trainer_batch_apply_manifest.json`
- `scripts/seed_melbourne_trainers.py`

### Mode B: post-launch acquisition and maintenance

`approved licensed discovery API/feed -> candidate URL/identity -> official website factual capture -> optional Gemini structuring -> ABR check -> geographic validation -> canonicalise/dedupe/suppress -> quality gate -> authorised publish or hold -> claim/correction/removal -> monitoring and refresh`

The same canonical records, suppression rules, quality gates, manifests, and
`/ops` evidence apply in both modes.

## 4. Post-Launch Source Decision & Commercial Inquiries

### 4.1 Preferred Commercial Feed: Thryv / Sensis SAPI & Inquiry Status

The primary commercial direction for licensed discovery is the Sensis business-search API (SAPI), a current successor API, or a Thryv Data scheduled feed. Sensis's official SAPI brochure confirms commercial programmatic access to >5 million Australian business listings and explicitly supports directory publishing use cases. However, public developer registration portals are currently offline.

**Active Operational Inquiry:**
- **Recipient:** `dataenquiry@thryv.com`
- **Scope Requested:** A commercial pilot dataset of 100–500 business records across Greater Melbourne dog training, behavior, and obedience categories.
- **Product Clarification:** Confirmed that Thryv's public MacroMatch and TotalCheck offerings are data cleansing, deduplication, and validation services rather than discovery feeds.
- **Contractual Pre-Requisites:** DTD may implement and enable the feed only after the supplier confirms in writing:
  1. the exact product and delivery method available to DTD;
  2. Greater Melbourne dog-training coverage and a sample schema;
  3. commercial retention and public-display rights;
  4. search-engine indexation rights for individual profiles;
  5. permission to process supplied data through Google Cloud and Gemini;
  6. permission to contact a business specifically to claim, correct, or remove its profile;
  7. attribution, branding, refresh, correction, suppression, and deletion obligations;
  8. post-contract retention or deletion requirements; and
  9. price, minimum commitment, quota, and pilot terms.

### 4.2 Google Web Search Products Enquiry & Custom Search API Deprecation

As part of DTD's discovery evaluation, the Google search ecosystem was assessed for lawful business URL discovery:
- **Custom Search JSON API Deprecation:** Google has officially deprecated the legacy Custom Search JSON API for new customers.
- **Official Enterprise Inquiry:** An official request has been submitted via Google's Web Search Products interest form.
- **Contractual Scope Sought:** The submission explicitly requests contractual permission to query full-web search, permanently retain canonical destination website URLs, and ingest factual business data from first-party trainer websites.
- **Strict Compliance Boundary:** The request explicitly excludes any copying, caching, or persistence of Google search result snippets, Google ranking algorithms, Google-cached pages, or Google-hosted imagery/photos. Persistent ingestion from Google Maps/Places API and Gemini Search Grounding remains strictly forbidden.

### 4.3 Post-Launch Sourcing Pivot: First-Party Registration (/submit) as Primary Growth CTA

Because post-launch automated third-party ingestion is not yet finalized due to pending commercial agreements with Thryv and Google:
- **Launch Posture:** The platform launches with the accepted 20-profile Melbourne baseline and verified statutory ABR evidence.
- **Primary Acquisition Driver:** First-party manual trainer registration (`/submit`) serves as the active, primary post-launch CTA to expand directory inventory safely and lawfully.
- **Governed Review:** All self-submitted profiles pass through the deterministic ABR validation pipeline, Modulus 89 checksum verification, quality scoring threshold, and publish/hold gating before inclusion in directory search.

### 4.4 Fallback Source Order

If Sensis/Thryv and Google do not provide suitable written rights, use this order:

1. another licensed Australian business-data API/feed with the same written rights;
2. trainer submissions, profile claims, and owner-authorised URLs (`/submit`);
3. association or partner feeds only under explicit permission or compatible terms; and
4. bounded manual URL curation as a temporary bridge.

Do not silently substitute Brave, Serpex, generic SERP scraping, Google Places,
Gemini Search Grounding, social-network scraping, or an association directory.
Every new source requires a named approval record and evidence before network
use or persistence.

## 5. Processing Stages

1. **Admit source**: require an enabled approval record, reviewed terms,
   permitted uses, credential state, rate limits, and source-health identity.
2. **Capture candidate evidence**: retain provider record ID, lawful
   source URL, retrieval time, licence/contract reference, and bounded evidence
   needed to reproduce the decision. Never place credentials in a manifest.
3. **Extract facts**: capture supported business facts from the licensed feed
   and approved official website. Do not republish creative descriptions,
   photographs, logos, reviews, or testimonials without a separate licence.
4. **Structure safely**: Gemini may convert already-lawful source content into
   the canonical schema. Schema-invalid, timed-out, unsupported, or ambiguous
   output falls back or is held. Sensitive fields such as training philosophy
   require explicit source support and default to unspecified when uncertain.
5. **Verify geography and identity**: confirm Greater Melbourne service
   relevance and use ABR only for statutory ABN/name/status evidence.
6. **Resolve entity**: match exact ABN, normalised Australian phone, exact
   hostname boundary, and bounded fuzzy business-name/locality evidence.
7. **Suppress first**: reject any candidate matching `db.delisted_entities` or
   another source/contract suppression requirement.
8. **Apply quality gate**: AI confidence alone never publishes or verifies a
   profile. Publication requires separately obtained source, identity, location,
   and minimum-content evidence plus explicit apply authority.
9. **Write non-destructively**: never overwrite verified claimed-owner fields
   with provider or AI output. Conflicts go to hold/review.
10. **Record operations evidence**: persist run identity, source state,
    candidate outcome, duplicate/suppression result, degradation reason, and
    publication/hold result for `/ops`.

## 6. Post-Launch Loops

These are target cadences, not proof of deployed schedules:

| Loop | Initial cadence | Rule |
| --- | --- | --- |
| Licensed discovery | Monthly, then tune from yield/cost | Process only new or changed provider records through the complete pipeline. |
| Unclaimed profile refresh | Every 180 days | Recheck source availability and supported facts; fill gaps or hold conflicts without destructive overwrite. |
| Claimed-owner reconfirmation | Rolling every 12 months | Ask the owner to confirm details; do not let provider or AI data silently replace owner-confirmed fields. |
| Data-quality assertions | Daily | Detect missing required fields, invalid phones/URLs, duplicate identities, stale evidence, dead domains, and source-health degradation. |

Retries must be idempotent and bounded. Routine healthy runs remain quiet;
actionable failures, stale sources, suppression events, and review holds appear
in `/ops`.

## 7. Activation Gate

The licensed acquisition engine remains disabled until all of the following are
evidenced:

1. written supplier rights are stored and reviewed;
2. `backend/data/ingestion_source_approvals.json` contains the exact approved uses;
3. a source-specific adapter and fixtures exist;
4. dry-run manifests prove provenance without writes;
5. duplicate, malformed, revoked, suppressed, expired-contract, and outage cases pass;
6. no provider or private evidence leaks through the public API;
7. `/ops` shows source health and actionable exceptions;
8. authenticated Cloud Scheduler/Tasks execution is verified; and
9. the owner explicitly authorises production activation and any expansion seed.

Launching the website with the accepted initial supply and trainer-submission
path does not depend on completing this post-launch supplier integration.

## 8. Official Boundary References

- Sensis currently advertises a business-search API: `https://www.sensis.com.au/products`
- Thryv Data public product material: `https://www.sensisdata.com.au/`
- Thryv Data sales contact & SAPI brochure enquiry: `dataenquiry@thryv.com`
- Google Places storage/attribution policy: `https://developers.google.com/maps/documentation/places/web-service/policies`
- Google Custom Search JSON API deprecation notice: `https://developers.google.com/custom-search/v1/overview`
- Google Web Search Products interest form: `https://developers.google.com/custom-search`
- Gemini API additional terms, including Search Grounding restrictions: `https://ai.google.dev/gemini-api/terms`
- ABR Web Services agreement: `https://abr.business.gov.au/Tools/WebServicesAgreement`

External terms can change. Recheck the controlling agreement before approving
a source, renewing a contract, or broadening a permitted use.
