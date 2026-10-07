# DTD Full Project Completion Plan

**Status:** active execution plan — 7 October 2026.  This is the single cross-project completion sequence. It supersedes treating matching, acquisition, website, automation and `/ops` as isolated finish lines; their detailed contracts remain authoritative.

## Current verified baseline

- Developer sandbox: Cloud Run API `dtd-api-dev-00021-dfd` and isolated frontend `dtd-web-dev-00004-c2n`, both at 100% traffic; the API `/api/health` reports an available database and the frontend bundle resolves only to the sandbox API.
- The sandbox ingestion scheduler `dtd-trainer-ingest-cron` is enabled at 02:00 Australia/Melbourne. Its OIDC subject, canonical regional audience and JSON content type now match the service contract. A real Cloud Scheduler dry-run returned HTTP 200, wrote a zero-mutation run record, and that record was deleted; a real acquisition run remains intentionally unaccepted.
- Sandbox runtime now uses `dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`, with only Vertex AI User and Secret Manager accessor roles required by the current runtime. The prior default Compute identity is no longer attached to Cloud Run runtime traffic (DF-013 resolved for sandbox).
- Matching local release gate passes with 532 isolated backend tests. The runner starts an isolated loopback MongoDB instance when one is not supplied, creates a UUID-named database, and removes both in `finally`. A focused follow-up test now makes its no-provider precondition explicit rather than inheriting a developer's sandbox email secret.
- The disposable M9 API/Ops runner has passed live validation, emergency/urgent triage, no-confirmed-match, expanded scope, live non-degraded Gemini, redacted/opaque context, forced context expiry, public profile, terminal follow-up/idempotency, protected Ops evidence, and public-fixture removal. It created only UUID-prefixed fixtures, used no recipient email, and removed every created record. Matching events and contexts now write BSON expiry dates; sandbox TTL indexes exist and the sandbox-only legacy conversion found no strings to convert.
- `run_sandbox_matching_parity.sh` now proves the live AI/fallback boundary with one immutable, UUID-namespaced fixture: normal Gemini, a temporary developer-sandbox invalid-model fallback and restored Gemini all produced the same candidate and capability reason. The fallback was visible in protected Ops, `gemini-3.5-flash` was restored, and every record created by the run was removed.
- The isolated frontend has passed its 49-test/build gate and a browser submission of the live questionnaire to a disposable matching result and profile handoff. It presents the guided owner path, reaches only the sandbox API, and now refuses to claim a terminally undeliverable enquiry was sent. The fixture and all associated match records were removed and verified absent. The final protected-enquiry submission remains a just-in-time owner-confirmation action.

## Completion rule

DTD is not complete until every applicable item below is independently evidenced `DONE` in the developer sandbox, all verified open findings are closed or explicitly superseded by an owner decision, and production is separately authorised. Passing code tests, a Cloud Run health response, a scheduler job, or a rendered screen alone is insufficient.

## Execution order

| Phase | Scope and work | Exit evidence |
| --- | --- | --- |
| 0 | Establish one current-state register; reconcile stale matching records, current sandbox revision, scheduler/IAM and code branch. | This document, current-state entries and a clean exact commit map agree. |
| 1 | Release safety: dedicated sandbox runtime identity, least privilege, provider recovery registry, Cloud Build/Actions modernisation, dependency remediation plan, repeatable safe deploy with no hidden scheduler/IAM mutation. | Sandbox deploy/recovery drill, remote CI, dependency evidence, no use of default runtime identity. **Runtime identity and deployment/scheduler split are complete; CI, dependency and recovery work remains.** |
| 2 | Trainer supply and acquisition: match-ready declaration/onboarding, claim/correction/suppression lifecycle, lawful source evidence, scheduler observability, capacity freshness and query/index proof. | Disposable ingestion run and rerun; trainer declaration→projection→correction→exclusion journey; `/ops` evidence. |
| 3 | Owner website: one mobile-first owner entry route, accessible structured questionnaire, config failure state, truthful public copy, navigation/header/metadata/SEO repair, profile and enquiry handoff. | Desktop/mobile browser paths, keyboard/accessibility checks, failure states, rendered metadata and no private URL content. |
| 4 | Matching and safety: deterministic eligibility, paid-neutral AI/fallback parity, exact 0.05 presentation, thin-supply disclosure, urgent routes/provider freshness, notification retry and anti-gaming. | All M0–M6/M8 fixtures plus sandbox responses/records and truthful `/ops` states. |
| 5 | Operations and automation: protected `/ops` controls, audit records, delivery retry, scheduler execution/disable/recovery, SEO/tier/revenue evidence and exception-led operator workflows. | Four recovery drills, sanitised read models, data retention/cleanup proof, no unattended failing loop. |
| 6 | Sandbox acceptance: create uniquely prefixed disposable records only; trace owner→match→profile→enquiry→notification/failure→`/ops`; delete every fixture and verify zero remaining records/UI exposure. | M9 matrix completed, before/after counts, cleanup audit evidence, mobile/desktop captures and independent audit. |
| 7 | Production gate: only after the owner separately authorises it. Use zero-traffic revision, safe smoke tests, recovery/rotation evidence and no-charge commercial checks. | M10 canary, live-safe acceptance and explicit owner production authority. |

## Non-negotiable controls

1. Test data is namespaced, has an expiry/cleanup owner, is removed from every affected collection, and is checked absent from public UI and `/ops` before a sandbox run closes.
2. Matching remains eligibility → paid-neutral fit → deterministic presentation. Commercial state cannot influence eligibility or fit.
3. AI receives only permitted structured facts and sanitised owner input. It cannot invent capability, override safety or provide clinical/veterinary advice.
4. Scheduler, provider, IAM, billing and deployment actions are independently observable in `/ops` or their control plane; no deployment helper may silently mutate another workstream.
5. Public copy names its actual evidence basis; generic verified/vetted/reviewed/availability/safety claims are prohibited unless the exact displayed fact supports them.
6. Production, live charges, irreversible credential revocation, legal-policy changes and destructive real-data actions remain explicit owner gates.

## Immediate active sequence

1. On owner confirmation, complete only the final browser-submitted protected-enquiry action with a disposable fixture; keep all UI-visible test data namespaced and prove its removal. Browser result/profile and API/Ops terminal-delivery evidence are accepted, but the final browser submit is a representational external action.
2. Design a namespaced, approved-source ingestion acceptance run and rerun. The scheduler transport dry-run is complete; do not use a real business source until its acquisition authority, expected record disposition and cleanup plan are explicit.
3. Complete the remaining DF work in the cross-project ledger below, beginning with CI/dependency and privacy/safety acceptance blockers.

## Cross-project finding ledger

This is a working completion ledger, not a claim that every repository statement has been freshly audited. `DONE` has direct 6 October evidence; `PARTIAL` means code or a bounded sandbox segment works but the full workflow is not accepted; `OPEN` needs implementation or acceptance evidence.

| Finding(s) | Phase | State | Completion evidence still required |
| --- | --- | --- | --- |
| DF-001, DF-007 | 1, 7 | OPEN | Retire/confirm obsolete release-hosting surfaces after an owner-approved production inventory; do not change DNS or production hosting during sandbox work. |
| DF-003, DF-011, DF-020 | 3 | PARTIAL | The isolated `dtd-web-dev` frontend deploys the guided path, has browser-submitted result/profile evidence, and its bundle calls only the sandbox API. Only the confirmation-gated browser protected-enquiry submission remains. |
| DF-004, DF-008 | 2, 5 | OPEN | Controlled SEO publication and attribution evidence; preserve the fail-closed legacy corpus until evidence supports a disposition. |
| DF-005 | 5, 7 | OPEN | No-charge payment-provider acceptance only after the owner authorises commercial testing. |
| DF-006 | 1, 6 | PARTIAL | The self-contained local isolated suite and live API/Ops M9 matrix pass; expand to browser-submitted journey, automation/recovery and remote-CI acceptance. |
| DF-009 | 1 | OPEN | Fresh local audit reports 98 advisories; migrate from the legacy frontend toolchain and remediate in tested batches. |
| DF-010 | 1 | PARTIAL | Current workflow uses v7 actions; confirm a fresh remote Verify run after the authorised feature branch is synced. |
| DF-012 | 1 | DONE | Retain the scoped build-identity evidence; recheck only when source deployment identity changes. |
| DF-013 | 1 | DONE | Dedicated sandbox runtime identity deployed and live-health checked; keep default Compute identity out of runtime traffic. |
| DF-014 | 2 | PARTIAL | Read-only production corpus audit before any production promotion. |
| DF-015 through DF-019, DF-021, DF-022, DF-026 | 4, 6 | PARTIAL | Disposable M9 now passes API/Ops triage, expansion, live Gemini, expiry, protected follow-up and cleanup; controlled same-fixture Gemini/fallback parity and browser result/profile evidence now pass. Supply completeness, provider freshness and final confirmation-gated browser enquiry work remain. |
| DF-027 | 1, 4 | DONE | The v2-aware isolated release suite now passes all 532 tests and starts its own disposable loopback MongoDB instance. Keep the suite in the deploy preflight. |
| DF-028 | 4, 5, 6 | PARTIAL | Sandbox writes BSON expiry dates, has TTL indexes, completed a no-op legacy conversion and passed forced-expiry M9 evidence. Any production conversion remains a separate owner gate. |
| DF-024, DF-025 | 4 | OPEN | Verified urgent-provider data freshness/correction lifecycle, safety UI, and decision on the constrained Maps/Places emergency-discovery exception before implementation. |
| DF-017 | 5, 6 | PARTIAL | Provider-safe notification failure/retry test that cannot send to a real trainer, with Ops and idempotency evidence. |
