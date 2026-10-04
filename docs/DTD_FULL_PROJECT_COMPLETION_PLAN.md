# DTD Full Project Completion Plan

**Status:** active execution plan — 5 October 2026.  This is the single cross-project completion sequence. It supersedes treating matching, acquisition, website, automation and `/ops` as isolated finish lines; their detailed contracts remain authoritative.

## Current verified baseline

- Developer sandbox: `dogtrainersdirectory-dev`, Cloud Run `dtd-api-dev-00007-p8j`, 100% traffic, `/api/health` database available.
- The sandbox ingestion scheduler `dtd-trainer-ingest-cron` is enabled at 02:00 Australia/Melbourne and calls the authenticated internal ingestion endpoint.
- Sandbox runtime has Vertex AI User access. It still uses the default Compute service account; DF-013 remains open until replaced with a dedicated least-privilege runtime identity.
- Matching local release gate passes: `1d0acb4`, 530 isolated backend tests; the runner creates a UUID-named loopback database and deletes it in `finally`.
- Matching remains sandbox-unaccepted until its disposable live matrix, records, UI and `/ops` evidence pass.

## Completion rule

DTD is not complete until every applicable item below is independently evidenced `DONE` in the developer sandbox, all verified open findings are closed or explicitly superseded by an owner decision, and production is separately authorised. Passing code tests, a Cloud Run health response, a scheduler job, or a rendered screen alone is insufficient.

## Execution order

| Phase | Scope and work | Exit evidence |
| --- | --- | --- |
| 0 | Establish one current-state register; reconcile stale matching records, current sandbox revision, scheduler/IAM and code branch. | This document, current-state entries and a clean exact commit map agree. |
| 1 | Release safety: dedicated sandbox runtime identity, least privilege, provider recovery registry, Cloud Build/Actions modernisation, dependency remediation plan, repeatable safe deploy with no hidden scheduler/IAM mutation. | Sandbox deploy/recovery drill, remote CI, dependency evidence, no use of default runtime identity. |
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

1. Build the disposable sandbox acceptance harness with explicit create/read/cleanup verification and `/ops` correlation.
2. Run the matching M9 matrix against revision `00007-p8j`; repair every observed UI/API/persistence/automation discrepancy.
3. Replace the sandbox default Compute runtime identity and split deploy from scheduler/IAM setup.
4. Reconcile every DF-001 through DF-027 item into phases 1–7, remove stale findings only with new evidence, and execute highest-risk blockers first.
