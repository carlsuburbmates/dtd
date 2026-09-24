# DTD Documentation

**Reconciled:** 24 September 2026
**Scope:** the main Dog Trainers Directory repository. The separately deployed First Leash application owns its own product documentation.

This folder is both the map of DTD's authoritative documentation and a readable synthesis of the project. The synthesis below introduces no independent facts: every substantive statement is governed by one of the linked state, constraint, decision, or specification documents.

## Read this first

DTD is a free-to-dog-owners directory and guided matching service for Greater Melbourne. Trainers can hold free listings or buy flat-price visibility products; DTD never charges owners and never takes commissions or per-lead fees. The directory is publicly deployed and its core owner, trainer, matching, billing, suburb-catalogue, and operator surfaces exist, but commercial launch gates and several operational gaps remain. "Current" therefore means evidenced implementation state, not owner acceptance of the final product.

The immediate target is to make that existing system safe and dependable for a solo operator: maintain the seeded production suburb catalogue, correct SEO indexation controls, repair stale automated loops and broken messaging paths, reconcile `/ops` promises with its real bounded actions, clean questionable trainer records, remediate the documented dependency-security backlog, and switch Stripe to live mode only with the trial anchor and refund safeguards set together. Longer-term automation, demand-based pricing, additional products, and broader distribution remain vision items rather than commitments.

The First Leash remains a separate application at `learn.dogtrainersdirectory.com.au`. The relationship is a branded, static, query-free link in each direction. Behavioural dossier data stays on the user's device and is never transferred in the URL. The Google Cloud technical migration requested during the Google for Startups review is complete: Firebase Hosting serves the frontend in project `gen-lang-client-0028123502`, Cloud Run serves the API, and the public domain routes through the Google stack. An isolated developer staging sandbox (`dogtrainersdirectory-dev` and MongoDB Atlas `dtd-sandbox`) provides safe pre-production testing and development. The program application remains subject to Google's manual re-review; no approval or credit award is recorded here.

## Authority map

| Document | What it answers | When to read it |
| --- | --- | --- |
| [DTD_CURRENT_STATE.md](DTD_CURRENT_STATE.md) | What code, tests, deployment and captured runtime evidence show now | Before changing or reporting the product |
| [DTD_TARGETED_POST_LAUNCH_STATE.md](DTD_TARGETED_POST_LAUNCH_STATE.md) | The concrete next build and operating target | When choosing or implementing near-term work |
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
        v
VISIONISED TARGET STATE
trigger-based expansion, richer automation and additional commercial or
distribution surfaces only after evidence and explicit approval
```

## Maintenance rule

Update the authoritative source first, then update this synthesis. README must never create a new fact, number or decision. Before merging documentation changes, check README against every source it summarises and check the authoritative documents against one another. Verified implementation findings left unresolved during a task go in `DTD_CURRENT_STATE.md` with evidence, deferral reason and next action; remove them when verified closed, using git history as the audit trail. The decision register remains for decisions, not a bug backlog. A finding list is not proof of a comprehensive code audit. Historical and process material belongs under the repository-root `archive/`, entirely outside the active `docs/` tree. Routine searches exclude that archive; inspect it only on explicit archival-research request.
