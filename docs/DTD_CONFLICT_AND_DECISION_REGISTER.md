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

## CDR-017 — Developer Staging Sandbox Environment (GCP & MongoDB Atlas)

- **Date/status:** 2026-09-25 — locked architecture & implemented sandbox baseline.
- **Decision:** Establish an isolated staging sandbox environment comprising GCP project `dogtrainersdirectory-dev` and a separate MongoDB Atlas project/cluster `dtd-sandbox` (M0 Free tier, AWS Sydney `ap-southeast-2`). Runtime secrets are managed strictly in Google Secret Manager within `dogtrainersdirectory-dev`. Production project `gen-lang-client-0028123502` and live MongoDB cluster `DTD` remain strictly isolated from experimentation. New feature development, CI/CD automated test builds, and simulated operational workflows target this sandbox before production promotion.
- **Evidence:** Active GCP project `dogtrainersdirectory-dev` (Project Number: `625222421634`), billing account `0104B3-AB5AF0-8F0A01` linked; core serverless APIs enabled (`run.googleapis.com`, `secretmanager.googleapis.com`, `cloudbuild.googleapis.com`, `artifactregistry.googleapis.com`); Secret Manager containing 8 isolated sandbox secrets; live pymongo connection test to `dtd-sandbox` cluster v8.0.32 passing in session.
- **Rationale:** Protects live directory data, Stripe live billing, and public domain uptime from developer and AI experimentation errors; preserves zero-cost serverless baseline ($0 idle cost); upholds solo-operator safety.
- **Supersedes:** The single-project live-only cloud architecture and any assumption that testing occurs directly on production Cloud Run or live MongoDB.
- **Affected:** `DTD_CURRENT_STATE.md`, `specs/OPS_AND_OBSERVABILITY.md`, `DTD_TARGETED_POST_LAUNCH_STATE.md`, `README.md`.

## CDR-018 — Owner-to-trainer matching system model

- **Date/status:** 2026-09-26 — locked direction; implementation and verification open.
- **Decision:** DTD matching is an AI-assisted system whose normal matches should run without manual owner intervention. It has three independent layers: deterministic eligibility determines who may enter the candidate set; AI-assisted, paid-neutral fit assesses suitability for a particular owner and dog; deterministic presentation orders suitable candidates, with commercial status permitted only inside the existing 0.05 comparable-fit tiebreak. The matching decision contract and scenario evaluation precede any platform redesign; Google architecture is a dependent implementation decision, not a parallel product workstream.
- **Evidence:** explicit owner direction in the owner–trainer matching session; matching code and documentation audit; established workstream in `specs/MATCHING_AND_RANKING.md`.
- **Rationale:** natural-language behavioural needs and sparse supply require useful semantic reasoning, while legitimacy, safety, fairness, privacy and commercial boundaries require predictable, auditable rules. The model keeps human work to visible exceptions and systemic quality oversight.
- **Supersedes:** any description of matching as AI-optional decoration, an undifferentiated ranking calculation, or a system where commercial state can enter eligibility or raw fit.
- **Affected:** matching specification; owner questionnaire and results UI; match API/services; trainer fact model; match/outcome records; notifications; `/ops`; scenario evaluation and sandbox acceptance.

## CDR-019 — Urgent-support pathway is separate from ordinary trainer matching

- **Date/status:** 2026-09-26 — locked direction; implementation and provider coverage verification open.
- **Decision:** DTD will provide an AI-assisted urgent-support pathway and dedicated public support directory for Greater Melbourne. It routes owners to approved emergency-service or provider-information states before or alongside ordinary matching, but does not provide diagnosis, treatment, legal advice or a guarantee of provider availability. AI may classify among approved route states and present versioned safety information; it may not generate freeform medical/veterinary advice or override ordinary matching eligibility and fit rules.
- **Evidence:** explicit owner direction in the owner–trainer matching session; official Victorian emergency-service and provider-owned public information reviewed during planning.
- **Rationale:** urgent and safety-sensitive owner needs should have a low-friction route to current contact information without misrepresenting DTD as an emergency service, clinical provider or universal-coverage directory.
- **Supersedes:** the assumption that an urgent concern can be handled only through an ordinary trainer shortlist, or that a disclaimer alone permits AI-generated professional advice.
- **Affected:** matching specification; public support page; owner questionnaire/results; AI and fallback decision contracts; separate provider register; acquisition/refresh controls; privacy; `/ops`; sandbox acceptance.

## CDR-020 — Bounded Google Maps/Places urgent-support exception

- **Date/status:** 2026-09-26 — locked direction; implementation and product-specific terms verification open.
- **Decision:** CDR-008's Places/Maps exclusion is amended only for a user-initiated, session-scoped urgent-support discovery/navigation surface. It may request and display fresh Google Maps Platform content after an owner enters the relevant approved urgent-support route, subject to the exact selected product's terms. Google-sourced content must remain visibly attributed and separate from DTD content. It must not be persisted as DTD business data (other than a permitted Place ID where the applicable terms allow it), used to acquire trainers, create or refresh DTD trainer/provider records, substantiate DTD claims, alter DTD rankings, or enter Gemini prompts, outputs, model evaluation or training. DTD's own urgent-provider directory remains official-source based.
- **Evidence:** explicit owner challenge to the blanket rule in the owner–trainer matching session; Google Maps JavaScript API policy states that content storage is generally restricted, Place IDs are an exception, place names may not be persisted outside the user session, and displayed Maps content requires clear attribution.
- **Rationale:** live, geographically relevant navigation can reduce friction for an owner seeking urgent support without converting Google content into an unverified DTD recommendation, permanent inventory or AI-training data.
- **Supersedes:** the blanket reading of CDR-008 only for the CDR-020 urgent-support discovery/navigation surface. It does not supersede CDR-008's persistent trainer-acquisition prohibition.
- **Affected:** acquisition invariant and specification; matching urgent-support contract; future public support UI; privacy notice; Maps/Places implementation review; sandbox and `/ops` evidence.

## CDR-021 — Acquisition is the evidence authority for matchable trainer facts

- **Date/status:** 2026-09-26 — locked direction; implementation and field-level evidence verification open.
- **Decision:** Acquisition and matching are connected, but not merged. Acquisition automation distinguishes and maintains trainer identity/lifecycle facts, source-backed capability facts and non-matchable commercial/marketing data. Matching consumes only a deterministic match-ready projection of permitted, current capability facts and eligibility gates. A published profile is not automatically fit-eligible for every owner request, and matching AI may not invent, upgrade or repair trainer capability data. Paid status remains outside this projection except for the separately locked presentation tiebreak.
- **Evidence:** explicit owner clarification in the owner–trainer matching session; current trainer model contains specialties, service formats, serviced suburbs, catchment and philosophy fields, while the acquisition specification already owns source, quality, suppression and refresh controls.
- **Rationale:** trustworthy AI-assisted matching depends on the quality and provenance of the candidate facts it receives. Separating fact production from case-specific fit reasoning prevents profile prose, stale facts, AI confidence or commercial status from silently becoming recommendation evidence.
- **Supersedes:** any assumption that a published directory profile, freeform profile text or model-extracted value is automatically matchable.
- **Affected:** acquisition specification and automation; trainer schema/provenance; matching eligibility and AI inputs; correction/suppression/refresh; `/ops`; scenario fixtures and sandbox acceptance.

## CDR-022 — Trainer capability declaration determines matching capacity

- **Date/status:** 2026-09-26 — locked direction; onboarding, provenance and matching implementation open.
- **Decision:** A trainer's structured onboarding, claim or profile-update declaration is a primary source of matching capacity. DTD may use authorised acquisition to prefill capability fields, but the trainer can confirm, correct or complete the structured declaration. Their declared service areas, formats, specialties, life-stage suitability where relevant, philosophy/method boundaries and material constraints determine the owner needs for which the matching system may consider them. Each field records whether it came from an official source or trainer declaration and its last confirmation. Free text may explain or propose a value for trainer confirmation; it cannot independently create an unbounded matchable claim. Paid status never changes the declaration's matching effect.
- **Evidence:** explicit owner direction in the owner–trainer matching session; existing submission schema already accepts philosophy, specialties, formats, serviced suburbs and catchment fields.
- **Rationale:** the trainer is best placed to state the services they actually offer. Making this declaration explicit and consequential produces more relevant matches, clear trainer control and a maintainable acquisition-to-matching handoff without treating marketing prose as evidence.
- **Supersedes:** an interpretation of CDR-021 under which only externally sourced capability facts may influence matching capacity, or under which trainer capability fields are passive profile text.
- **Affected:** trainer onboarding, claim and profile-update flows; acquisition field provenance; matching projection and eligibility; AI inputs; trainer-facing disclosure; corrections/suppression; `/ops`; scenario fixtures and sandbox acceptance.

## CDR-023 — Targeted matching pipeline state is the implementation authority

- **Date/status:** 2026-09-26 — locked target; implementation and verification open.
- **Decision:** `DTD_TARGETED_MATCHING_PIPELINE_STATE.md` is the focused target-state authority for owner-to-trainer matching. It consolidates the matching model, trainer capability declaration, acquisition dependency, urgent-support pathway, bounded Maps/Places use, privacy/fairness rules, records, `/ops` evidence and sandbox acceptance. It guides implementation after the matching decision contract and scenario evaluation; it does not itself activate public behaviour or supersede separate production gates.
- **Evidence:** explicit owner request to create a targeted end state from the established matching workstream; CDR-018 through CDR-022 and the active matching/acquisition specifications.
- **Rationale:** one focused target prevents the matching pipeline from being implemented as disconnected form, AI, data, urgent-support and commercial-ranking changes.
- **Supersedes:** CDR-010's fixed active-authority count as it applies to this focused target, and the assumption that the broad post-launch target or matching specification alone is sufficient implementation authority for this cross-workflow pipeline.
- **Affected:** documentation map; targeted post-launch state; matching/acquisition implementation; trainer onboarding; owner UX; AI/fallback; urgent support; `/ops`; sandbox acceptance.

## CDR-024 — Weak-evidence matching outcome resolved by Decision Contract v2

- **Date/status:** 2026-09-27 — resolved by the delegated matching authority in `specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md`; implementation and sandbox acceptance remain open.
- **Decision:** the earlier planning language that AI or fallback should “decline to manufacture a match”, clarify, abstain, or return no suitable match did not itself select DTD's final weak-evidence outcome. Decision Contract v2 now selects versioned owner-visible states: `needs_clarification` for incomplete/contradictory input, `limited_local_results` with disclosed expansion where suitable supply exists, `no_confirmed_match` where current capability/fit evidence does not support a recommendation, and deterministic `degraded_*` states when AI is unavailable. A shortlist remains permitted when the contract's evidence conditions are met. These states must be truthful, privacy-safe, compatible across AI and fallback paths, and covered by fixtures and sandbox acceptance.
- **Evidence:** explicit owner challenge during independent-review analysis; review of CDR-018 and downstream planning language.
- **Rationale:** an independent critique is intended to strengthen or change the plan. Presupposing the outcome would turn a design hypothesis into a false owner decision and bias evaluation.
- **Supersedes:** only the weak-evidence-output language in CDR-018 and all downstream statements that make clarification, abstention, no-match or a prohibition on a recommendation the preselected general matching outcome. It does not weaken eligibility gates, commercial fairness, privacy, urgent-support safety routes, or the prohibition on AI inventing trainer capability facts.
- **Affected:** targeted matching state; matching and sandbox specifications; completion roadmap; current-state finding DF-023; proactive matching-assistance skill; Decision Contract v2 and scenario fixtures.

## CDR-025 — Standing owner authority and exception-driven execution

- **Date/status:** 2026-10-07 — owner-directed operating rule.
- **Decision:** Instructions and approvals given by the sole owner in this session remain usable for the specified work until revoked or materially changed. Agents should complete routine implementation, tests, documentation, commits, branch sync and authorised developer-sandbox actions without repeated yes/no questions. An external service or a nominally high-risk topic is not itself a new approval gate. Ask only for a genuinely new decision or authority, or an unavoidable credential or platform action-time confirmation. A password or one-time code must be completed by the owner in the trusted local sign-in flow, never supplied in chat. Keep production release, live charging, credential creation/revocation, destructive real-data changes and material legal/privacy policy changes subject to applicable owner authority when it has not already been granted.
- **Evidence:** the owner's 7 October instruction to remove unnecessary workflow blockers, carry out the best supported course, and stop requesting a fresh yes/no when the task already authorises the action.
- **Rationale:** repeated preflight reports and confirmation loops were delaying work in a one-owner project despite existing authorisation. Evidence and actual product boundaries remain necessary; redundant prompts do not.
- **Supersedes:** any interpretation of repository process rules requiring a new approval for every optional skill, backend edit, branch push, sandbox step or ordinary external action after the owner has already authorised the workflow.
- **Affected:** `AGENTS.md`, `.codex/skill-policy.toml`, the proactive owner-assistance skill, workstream handoffs and release sequencing.
