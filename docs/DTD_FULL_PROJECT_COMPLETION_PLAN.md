# DTD Full Project Completion Plan

**Status:** active execution plan — 5 October 2026.  This is the single cross-project completion sequence. It supersedes treating matching, acquisition, website, automation and `/ops` as isolated finish lines; their detailed contracts remain authoritative.

## Current verified baseline

- Developer sandbox: `dogtrainersdirectory-dev`, Cloud Run `dtd-api-dev-00012-bpc`, 100% traffic, `/api/health` database available.
- The sandbox ingestion scheduler `dtd-trainer-ingest-cron` is enabled at 02:00 Australia/Melbourne. Its OIDC subject, canonical regional audience and JSON content type now match the service contract. A real Cloud Scheduler dry-run returned HTTP 200, wrote a zero-mutation run record, and that record was deleted; a real acquisition run remains intentionally unaccepted.
- Sandbox runtime now uses `dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com`, with only Vertex AI User and Secret Manager accessor roles required by the current runtime. The prior default Compute identity is no longer attached to Cloud Run runtime traffic (DF-013 resolved for sandbox).
- Matching local release gate passes: `1d0acb4`, 530 isolated backend tests; the runner creates a UUID-named loopback database and deletes it in `finally`.
- The first live, disposable matching acceptance passed twice: a unique declared-capability trainer was returned by `/api/match`, a sanitised match event appeared in protected matching Ops, and the trainer/event/context/fallback event were deleted and then confirmed absent from the public trainer endpoint. The remaining M9 matrix, rendered owner UI, profile/enquiry lifecycle and retention expiry are still unaccepted.

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

1. Expand the passing disposable acceptance runner into the full M9 matrix: validation, safety triage, exact/expanded/no-match, AI degradation, context, profile and enquiry state; keep each run self-cleaning and public-absence checked.
2. Repair and visually verify the owner web journey (DF-003, DF-011, DF-020) from navigation through mobile questionnaire, error/degraded states, results and profile handoff.
3. Design a namespaced, approved-source ingestion acceptance run and rerun. The scheduler transport dry-run is complete; do not use a real business source until its acquisition authority, expected record disposition and cleanup plan are explicit.
4. Complete the remaining DF work in the cross-project ledger below, beginning with CI/dependency and privacy/safety acceptance blockers.

## Cross-project finding ledger

This is a working completion ledger, not a claim that every repository statement has been freshly audited. `DONE` has direct 5 October evidence; `PARTIAL` means code or a bounded sandbox segment works but the full workflow is not accepted; `OPEN` needs implementation or acceptance evidence.

| Finding(s) | Phase | State | Completion evidence still required |
| --- | --- | --- | --- |
| DF-001, DF-007 | 1, 7 | OPEN | Retire/confirm obsolete release-hosting surfaces after an owner-approved production inventory; do not change DNS or production hosting during sandbox work. |
| DF-003, DF-011, DF-020 | 3 | PARTIAL | Local owner navigation now targets guided matching, config fails closed, inputs/results are labelled/announced, and client-side route metadata is set. A deployed frontend plus desktop/mobile keyboard/browser evidence is still required. |
| DF-004, DF-008 | 2, 5 | OPEN | Controlled SEO publication and attribution evidence; preserve the fail-closed legacy corpus until evidence supports a disposition. |
| DF-005 | 5, 7 | OPEN | No-charge payment-provider acceptance only after the owner authorises commercial testing. |
| DF-006 | 1, 6 | PARTIAL | Local isolated suite and one live matching cycle pass; expand to browser/API/automation/recovery acceptance in CI. |
| DF-009, DF-010 | 1 | OPEN | Supported frontend toolchain/dependency remediation plus green remote workflow on the current runner image. |
| DF-012 | 1 | DONE | Retain the scoped build-identity evidence; recheck only when source deployment identity changes. |
| DF-013 | 1 | DONE | Dedicated sandbox runtime identity deployed and live-health checked; keep default Compute identity out of runtime traffic. |
| DF-014 | 2 | PARTIAL | Read-only production corpus audit before any production promotion. |
| DF-015 through DF-019, DF-021 through DF-023, DF-026, DF-027 | 4, 6 | PARTIAL | Full M0–M9 sandbox matrix, retained-record/expiry proof, UI acceptance and AI/fallback parity; the basic live match/record/Ops/cleanup cycle and local suite pass. |
| DF-024, DF-025 | 4 | OPEN | Verified urgent-provider data freshness/correction lifecycle, safety UI, and decision on the constrained Maps/Places emergency-discovery exception before implementation. |
| DF-017 | 5, 6 | PARTIAL | Provider-safe notification failure/retry test that cannot send to a real trainer, with Ops and idempotency evidence. |
