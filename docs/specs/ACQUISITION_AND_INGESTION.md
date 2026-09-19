# Acquisition and Ingestion

## Purpose and authority

This specification governs how DTD discovers, verifies, enriches, publishes, refreshes and suppresses trainer listings. The operating goal is low-touch growth for a solo owner without weakening source rights, evidence, quality or trainer control.

## Approved source classes

1. Trainer self-submission and claim through DTD.
2. Owner-authorised official trainer website URLs.
3. An official/licensed business-data API or feed with written rights covering retention, public display, indexation, processing, contact, correction, suppression and post-contract obligations.
4. Association/partner feeds only under explicit permission or compatible terms.
5. Bounded manual URL curation as a temporary bridge.

ABR is approved for statutory ABN/name/status verification, not discovery. Google Places/Maps content and Gemini Search Grounding are excluded from persistent acquisition. Generic SERP scraping and unapproved directory copying are excluded.

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

### Post-launch acquisition

```text
approved licensed discovery source
→ candidate identity/URL
→ official-site factual capture
→ optional Gemini structuring
→ ABR and geography checks
→ canonicalise/dedupe/suppress
→ quality gate
→ publish or hold
→ claim/correct/remove
→ monitor and refresh
```

This mode is designed but remains disabled until a licensed source contract, adapter, dry-run evidence, authenticated scheduling and explicit activation exist. `/submit` is the active primary growth path meanwhile.

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

## Source decisions

- Thryv/Sensis remains a potential preferred licensed discovery direction, pending written commercial and usage terms.
- Google Web Search Products was an inquiry path, not approved acquisition authority.
- MacroMatch/TotalCheck may be considered for validation only; they are not assumed discovery feeds.
- A new source requires a named decision record before network use or persistence.

## Activation and acceptance

- Dry-run manifest shows source, rights, dedupe, suppression and quality outcomes.
- Apply is idempotent and produces audit evidence.
- Failed extraction/provider calls degrade to hold/retry, not speculative publication.
- UI → API → persisted profile/evidence → notification/fallback → `/ops` is verified.
- Production scheduling is authenticated and its live cadence is proven separately from code.
