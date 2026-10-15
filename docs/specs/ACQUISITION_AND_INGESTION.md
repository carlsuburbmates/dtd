# Acquisition and Ingestion

## Purpose and authority

This specification governs how DTD discovers, verifies, enriches, publishes, refreshes and suppresses trainer listings. The operating goal is low-touch growth for a solo owner without weakening source rights, evidence, quality or trainer control.

## Approved source classes

1. Trainer self-submission and claim through DTD.
2. Owner-authorised official trainer website URLs.
3. An official/licensed business-data API or feed with written rights covering retention, public display, indexation, processing, contact, correction, suppression and post-contract obligations.
4. Association/partner feeds only under explicit permission or compatible terms.
5. Bounded manual URL curation as a temporary bridge.

ABR is approved for statutory ABN/name/status verification, not discovery. Google Places/Maps content and Gemini Search Grounding are excluded from persistent acquisition. CDR-020 allows a separate, session-scoped Google-attributed Maps/Places urgent-support discovery/navigation surface, subject to the applicable product terms; it cannot create or update DTD trainer/provider records, claims, AI inputs, model evaluation/training or rankings. Generic SERP scraping and unapproved directory copying are excluded.

## Current operating modes

### Launch baseline

```text
owner-approved official URL
→ bounded factual capture
→ ABR identity/status check
→ canonicalise/dedupe/suppress
→ quality gate
→ authorised publish or hold
→ /ops evidence
```

Twenty authorised Greater Melbourne profiles have local reproducible manifests and scripts. This does not convert older records into equally evidenced profiles.

### Post-launch autonomous acquisition (Dual-Engine Pipeline)

```text
Discovery source (explicit / queue / seed)
→ Engine 1: Batch Ingestion Orchestrator
   ├ Polite crawl (2.05s delay, robots.txt, 5s/10s timeouts)
   ├ Structured extraction via Gemini on Vertex AI
   ├ ATO Modulus 89 checksum & ABR Web Services check
   ├ 4-Tier deduplication (ABN → domain → phone → name+suburb)
   └ Claimed/paid profile protection (never overwritten)
→ Engine 2: Supervisory Verification Guardian
   ├ Global uniqueness verification (zero duplicates mandate)
   ├ Statutory truth enforcer (DF-014: 100% active verified ABR required to publish)
   ├ Anti-hallucination check (placeholder domain/name/phone rejection)
   └ Auto-remediation & persistent audit logging
→ State persistence in db.trainers, db.source_ingestion_state, db.ingestion_runs
→ Operations Console (/ops) evidence-led telemetry & supervisory audit visibility
```

#### Execution and Trigger Boundaries

1. **Cloud Scheduler Specification (Serverless Cron):**
   - Specification targets Cloud Scheduler job `dtd-trainer-ingest-cron` daily at 2:00 AM AEST.
   - Authenticated via OIDC Service Account (`dtd-scheduler-invoker@dtd-api-dev.iam.gserviceaccount.com`).
   - Targets `POST /api/internal/jobs/trainer-ingest` with token verification via `_require_cloud_scheduler_oidc`.
   - Note: Repository code implements and unit-tests the endpoint; live Cloud Scheduler configuration in Google Cloud remains unverified without authenticated control-plane evidence.
   - Operations Console (`/ops`) remains evidence-led and read-only; no live mutation route is exposed.

## Processing contract

1. **Admit source:** enabled approval record, reviewed terms, permitted uses, rate limits and health identity.
2. **Capture evidence:** provider ID, lawful source URL, retrieval time, licence/approval reference and bounded reproducibility evidence; never credentials.
3. **Extract facts:** public business facts only. Do not republish creative descriptions, logos, photographs, reviews or testimonials without rights.
4. **Structure safely:** Gemini may structure already-lawful content. Invalid, timed-out, unsupported or ambiguous output falls back or is held.
5. **Verify:** Greater Melbourne relevance and ABR statutory identity/status.
6. **Resolve entity:** exact ABN, normalised phone, exact hostname, then bounded name/locality evidence.
7. **Suppress first:** delisted/correction/source-contract suppression is checked before publish.
8. **Quality gate:** supported fields, contactability, provenance and policy state determine publish/hold; AI confidence is not proof.
9. **Persist atomically:** canonical record plus source evidence, decision and audit event.
10. **Trainer control:** claim, correct and remove paths remain available.
11. **Refresh:** source-specific cadence and deletion/correction obligations apply; stale evidence surfaces in `/ops`.

## Match-ready capability projection

Acquisition and owner-to-trainer matching are connected but remain separate workflows. Acquisition establishes and maintains trainer facts through authorised official-source capture and the trainer's own onboarding/claim declaration. Matching consumes a deterministic, versioned projection of those facts; it does not discover, infer or repair them while serving an owner.

1. **Identity and lifecycle gates:** publication, suppression/delisting, policy state, statutory identity/status where required, contact readiness and source freshness determine whether a trainer can enter the matchable pool.
2. **Matchable capability facts:** only field-level, source-backed or trainer-confirmed facts may support matching: serviced suburbs/catchment, supported service formats, specialties, stated training philosophy/method boundaries and explicitly modelled availability constraints. Each must retain its source/evidence reference, retrieval or confirmation time, normalised value and evidence state.
3. **Non-matchable data:** paid tier, sponsorship, billing state, marketing prose, unverified reviews, generic profile completeness, AI confidence and unsupported inferences never enter eligibility or raw fit. They may have separate presentation or operational roles only where another contract expressly permits them.
4. **Automation boundary:** Gemini may structure an already lawful source into a proposed field value, but the acquisition quality gate—not Gemini—determines whether that field becomes matchable. A correction, suppression, failed refresh or stale capability fact removes or limits that fact from the projection and is visible in `/ops`.
5. **Matching boundary:** Gemini receives only the eligible candidate set and the permitted projected fields. It cannot add a specialty, widen a catchment, infer a service format or promote a profile whose required matching facts are unknown, stale or unsupported.

The matching decision contract must define the per-concern minimum evidence required before a trainer may be considered. The implementation may materialise this as a projection or derive it from canonical trainer records, but it must preserve the same field-level provenance, invalidation and audit evidence.

### Trainer capability declaration

Trainer onboarding and claim/update flows must collect a structured, explicit capability declaration. It is a first-class source of matching capacity, not optional marketing copy. A trainer declares and confirms the areas they serve, service formats, concerns/specialties, supported dog life stages where relevant, training philosophy/method boundaries, in-home or facility constraints, and any material availability constraints. The declaration must explain that these answers affect the owner requests for which DTD may consider the trainer.

Authorised acquisition may prefill these values from an official source, but the trainer can confirm, correct or complete them. The persisted field record identifies whether its basis is `official_source` or `trainer_declaration`, who or what last confirmed it, and when. A trainer update supersedes the earlier capability declaration for matching once it passes deterministic validation; a correction, suppression or stale-field rule can remove it from matching capacity.

Free text may explain a declared capability or be used to propose normalised values for trainer confirmation. It cannot alone create an unbounded specialty, service area or method claim. Paid tier never changes the declaration's matching effect.

## Source decisions

- Sensis/Thryv SAPI is confirmed discontinued as of 11 September 2026; it is not a current licensed-source candidate.
- Google Web Search Products outreach is closed: the available offers were not a viable or approved discovery authority, and Grounded Generation remains excluded under CDR-008.
- The CDR-020 Maps/Places exception is not an acquisition-source approval. It is available only after its isolated urgent-support UI has passed product-specific terms, attribution, retention/caching, privacy and sandbox checks; it does not authorise the legacy trainer-discovery adapter.
- MacroMatch/TotalCheck may be considered for validation only; they are not assumed discovery feeds.
- A new source requires a named decision record before network use or persistence.

## Activation and acceptance

- Dry-run manifest shows source, rights, dedupe, suppression and quality outcomes.
- Apply is idempotent and produces audit evidence.
- Failed extraction/provider calls degrade to hold/retry, not speculative publication.
- UI → API → persisted profile/evidence → notification/fallback → `/ops` is verified.
- Production scheduling is authenticated and its live cadence is proven separately from code.
