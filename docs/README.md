# DTD Documentation

**Reconciled:** 24 October 2026 (superseded handovers/audits archived; current R8 checkpoint and external Antigravity stream remain separate)
**Scope:** the main Dog Trainers Directory repository. The separately deployed First Leash application owns its own product documentation.

This folder is both the map of DTD's authoritative documentation and a readable synthesis of the project. The synthesis below introduces no independent facts: every substantive statement is governed by one of the linked state, constraint, decision, or specification documents.

## Read this first

DTD is a free-to-dog-owners directory and guided matching service for Greater Melbourne. Trainers can hold free listings or buy flat-price visibility products; DTD never charges owners and never takes commissions or per-lead fees. The directory is publicly deployed and its core owner, trainer, matching, billing, suburb-catalogue, and operator surfaces exist, but commercial launch gates and several operational gaps remain. "Current" therefore means evidenced implementation state, not owner acceptance of the final product.

The immediate target is to make that existing system safe and dependable for a solo operator: maintain the seeded production suburb catalogue, correct SEO indexation controls, repair stale automated loops and broken messaging paths, reconcile `/ops` promises with its real bounded actions, clean questionable trainer records, remediate the documented dependency-security backlog, and switch Stripe to live mode only with the trial anchor and refund safeguards set together. The owner-to-trainer matching pipeline is a separately governed targeted workstream: it must complete its decision contract, trainer-capability supply, safe AI/fallback states, urgent support and acceptance evidence before it can be called complete. Longer-term automation, demand-based pricing, additional products, and broader distribution remain vision items rather than commitments.

The First Leash remains a separate application at `learn.dogtrainersdirectory.com.au`. The relationship is a branded, static, query-free link in each direction. Behavioural dossier data stays on the user's device and is never transferred in the URL. Fresh DNS and HTTP checks confirm canonical `dogtrainersdirectory.com.au` is served through Firebase Hosting in project `gen-lang-client-0028123502`, with `/api/health` reaching the production Cloud Run API. The similarly named `.com` domain is separate in current DNS and serves a different Cloudflare/ASP.NET response; its relationship to DTD is unknown. The owner explicitly confirmed that the final developer sandbox is Cloud Run `dtd-api-dev` and `dtd-web-dev` in `dogtrainersdirectory-dev`, with Atlas `dtd_sandbox` (CDR-027). Firebase Hosting is production-only; authenticated control-plane reads show zero dev Hosting sites and only the main production site's live channel. The earlier missing-Firebase-sandbox requirement is superseded. Vercel's DTD Git connection was removed and verified; it is not a delivery path. The program application remains subject to Google's manual re-review; no approval or credit award is recorded here.

## Authority map

The active cross-project execution sequence is [DTD Full Project Completion Plan](DTD_FULL_PROJECT_COMPLETION_PLAN.md). It coordinates the detailed matching, acquisition, website, automation, Ops, sandbox and production contracts; it does not replace their locked decisions.

| Document | What it answers | When to read it |
| --- | --- | --- |
| [DTD_CURRENT_STATE.md](DTD_CURRENT_STATE.md) | What code, tests, deployment and captured runtime evidence show now | Before changing or reporting the product |
| [DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md](DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md) | Owner-approved R0–R13 stage sequence and separate engineering/product/operational/business outcomes | Stage navigation; existing authority documents still govern implementation |
| [DTD_NEXT_SESSION_HANDOVER.md](DTD_NEXT_SESSION_HANDOVER.md) | Exact resume checkpoint, current sandbox, retained work and next authorized stage | Resuming after the requested handover |
| [DTD_ROADMAP_EXECUTION_REGISTER.md](DTD_ROADMAP_EXECUTION_REGISTER.md) | Current stage gates, next safe action and review checkpoint | Resuming roadmap execution |
| [DTD_CODEX_GAP_REGISTER.md](DTD_CODEX_GAP_REGISTER.md) | Deduplicated P0–P3 findings mapped to roadmap stages | Prioritizing fixes without creating parallel issue tracking |
| [DTD_ROADMAP_RECONCILIATION.md](DTD_ROADMAP_RECONCILIATION.md) | R-stage mapping to existing completion plans, findings and decisions | Reconciling existing plans |
| [R2_RELEASE_RECONCILIATION.md](R2_RELEASE_RECONCILIATION.md) | Exact merged main SHA, developer Cloud Run revisions, checks, safety flags, scheduler state and recovery evidence | Reviewing R2 consolidation and sandbox deployment |
| [R3_RELEASE_FOUNDATION.md](R3_RELEASE_FOUNDATION.md) | Exact R3 developer API release, dependency/source verification, health, scheduler, recovery limits and hosting/provider gaps | Reviewing R3 release foundation and current sandbox boundary |
| [R1_SANDBOX_RELEASE_EVIDENCE.md](R1_SANDBOX_RELEASE_EVIDENCE.md) | Exact DF-043 commit/build/revision, sandbox suppression checks, identity verification and R1 gate | Reviewing developer release evidence |
| [R1_FIXTURE_CLEANUP.md](R1_FIXTURE_CLEANUP.md) | Bounded synthetic fixture and temporary Scheduler cleanup record | Verifying sandbox fixture cleanup |
| [ANTIGRAVITY_GOOGLE_STARTUPS_RESEARCH_HANDOFF.md](ANTIGRAVITY_GOOGLE_STARTUPS_RESEARCH_HANDOFF.md) | Initial Antigravity prompt: establish a reusable Google for Startups program baseline, then independently assess the DTD application | Continuing the startup application review; not permission to send, publish, or mutate provider state |
| [GOOGLE_FOR_STARTUPS_PROGRAM_BASELINE.md](GOOGLE_FOR_STARTUPS_PROGRAM_BASELINE.md) | Official Google for Startups Cloud Program criteria, benefits, tiers, exclusions and evidence baseline | Evaluating startup program eligibility and re-review criteria |
| [DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md](DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md) | Phased funding, customer-funded bootstrap model, monetization engines, and roadmap scaling strategy | Commercial roadmap planning and refinement prior to execution |
| [GOOGLE_STARTUPS_ANTIGRAVITY_AUDIT.md](GOOGLE_STARTUPS_ANTIGRAVITY_AUDIT.md) | Independent review of current public evidence, official program criteria, and commercial-strategy assumptions | Auditing Antigravity's Google for Startups work |
| [DTD_TARGETED_POST_LAUNCH_STATE.md](DTD_TARGETED_POST_LAUNCH_STATE.md) | The concrete next build and operating target | When choosing or implementing near-term work |
| [DTD_TARGETED_MATCHING_PIPELINE_STATE.md](DTD_TARGETED_MATCHING_PIPELINE_STATE.md) | The concrete owner-to-trainer matching target, including acquisition, AI, urgent support and acceptance | Before changing matching, trainer capability data or urgent-support work |
| [DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md](DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md) | Matching work packages, completion rules and independent verification evidence | Before implementing or accepting matching-pipeline work |
| [specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md](specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md) | Versioned owner input, triage, eligibility, fit, presentation, privacy and acceptance rules | Before implementing or accepting a matching work package |
| [DTD_VISIONISED_TARGET_STATE.md](DTD_VISIONISED_TARGET_STATE.md) | Possible later evolution with explicit triggers | For strategy; never as an implementation instruction |
| [DTD_INVARIANTS_AND_CONSTRAINTS.md](DTD_INVARIANTS_AND_CONSTRAINTS.md) | Rules that every phase must preserve | Before any product, data, pricing, automation or ops change |
| [DTD_CONFLICT_AND_DECISION_REGISTER.md](DTD_CONFLICT_AND_DECISION_REGISTER.md) | What was decided, why, and what it superseded | When an old statement or ambiguity resurfaces |
| [specs/MONETISATION_AND_PRICING.md](specs/MONETISATION_AND_PRICING.md) | Products, prices, trial, inventory and refunds | Billing or sponsorship work |
| [specs/MATCHING_AND_RANKING.md](specs/MATCHING_AND_RANKING.md) | Fit scoring, commercial tiebreaks and fallbacks | Search or guided-match work |
| [specs/GEOGRAPHY_AND_CATCHMENTS.md](specs/GEOGRAPHY_AND_CATCHMENTS.md) | Canonical suburbs, regions and catchments | Geography, seed or inventory work |
| [specs/SEO_AND_INDEXATION.md](specs/SEO_AND_INDEXATION.md) | Indexation eligibility, sitemap and robots rules | Public discovery and suburb-page work |
| [specs/OPS_AND_OBSERVABILITY.md](specs/OPS_AND_OBSERVABILITY.md) | Operator workflows, automation and degraded states | `/ops`, alerts or production operations |
| [specs/SANDBOX_VERIFICATION_MATRIX.md](specs/SANDBOX_VERIFICATION_MATRIX.md) | Mandatory pre-flight checklist and sandbox gates | Testing features before production promotion |
| [specs/ACQUISITION_AND_INGESTION.md](specs/ACQUISITION_AND_INGESTION.md) | Lawful trainer sourcing, verification and lifecycle | Any data acquisition or profile ingestion work |

## Current checkpoint and historical records

The local independent-audit checkpoint is `389130e` on `codex/r8-audit-completion`; corrected runtime acceptance remains **PARTIAL**, not deployed. Use [R8 evidence](R8_END_TO_END_SANDBOX_ACCEPTANCE.md), [current state](DTD_CURRENT_STATE.md) and [execution register](DTD_ROADMAP_EXECUTION_REGISTER.md) for its scope. The owner sent the new `0701d09` commercial/roadmap handover to another Antigravity session; reconcile that session's returned commits before overlapping advancement. The active next-session and Google research handovers remain in `docs/`.

Twelve earlier acquisition/matching briefs and dated audit snapshots moved to the [24 October historical inventory](../archive/2026-10-24-superseded-handoffs-and-audits/README.md). Their evidence is preserved; their old resume/blocked/completed wording is not current execution authority. Follow historical links only for explicitly requested archival research. Current specs, M0–M10 criteria, decisions, release/recovery records and the new handover remain active.

The [generated-file audit](../archive/2026-10-24-superseded-handoffs-and-audits/GENERATED_FILE_AUDIT_2026-10-24.md) records completed private archival and current artifact-retention decisions. It is historical cleanup evidence, not a release or deletion authority.

## State progression

```text
CURRENT STATE
publicly deployed; core workflows implemented; commercial launch gated;
known data, SEO, messaging and operations gaps remain
        |
        v
TARGETED POST-LAUNCH STATE
truthful production data; bounded reliable operations; live billing with
cohort/refund safeguards; measurable SEO; clean cross-site separation
        |
        +--> TARGETED MATCHING PIPELINE STATE
             AI-assisted but deterministic-bound matching, acquisition and
             trainer-declaration facts, urgent support, privacy and sandbox evidence
        |
        v
VISIONISED TARGET STATE
trigger-based expansion, richer automation and additional commercial or
distribution surfaces only after evidence and explicit approval
```

## Maintenance rule

Update the authoritative source first, then update this synthesis. README must never create a new fact, number or decision. Before merging documentation changes, check README against every source it summarises and check the authoritative documents against one another. Verified implementation findings left unresolved during a task go in `DTD_CURRENT_STATE.md` with evidence, deferral reason and next action; remove them when verified closed, using git history as the audit trail. The decision register remains for decisions, not a bug backlog. A finding list is not proof of a comprehensive code audit. Historical and process material belongs under the repository-root `archive/`, entirely outside the active `docs/` tree. Routine searches exclude that archive; inspect it only on explicit archival-research request.
