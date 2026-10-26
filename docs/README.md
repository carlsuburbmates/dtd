# DTD Documentation

**Reconciled:** 26 October 2026 — owner-approved documentation consolidation.
**Scope:** main Dog Trainers Directory repository. First Leash owns its separate education application and documentation.

## Start here

DTD's goal is a trustworthy, useful and financially sustainable Greater Melbourne trainer discovery and matching service, operated through automation with owner decisions by exception. Owner browsing, matching and contact remain free.

1. Read repository `AGENTS.md` for action authority and review gates.
2. Use the [execution register](DTD_ROADMAP_EXECUTION_REGISTER.md) for stage progress and the next authorised package.
3. Read [current state](DTD_CURRENT_STATE.md) for exact source/runtime checkpoints and unresolved DF/TD findings.
4. Apply the [invariants](DTD_INVARIANTS_AND_CONSTRAINTS.md), relevant specification and any applicable [decision record](DTD_CONFLICT_AND_DECISION_REGISTER.md).

R0–R3 scoped checkpoints remain accepted. Corrected R4–R8 runtime acceptance remains PARTIAL; source consolidation does not establish deployment or complete live workflows. The 25 October developer credential containment governs safe recovery. Ingestion activation, R9 production, R11 commerce, credential and source-rights changes retain their respective gates. Use the linked records for evidence rather than this navigation summary.

## Authority map

Each document has a distinct role. Specifications define requirements; current state records evidence; the execution register tracks progress. A discrepancy between implementation and an approved requirement is a finding, not permission to rewrite the requirement.

| Document | Owns |
| --- | --- |
| [End-to-end roadmap](DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md) | R0–R13 destinations, dependencies and exit contracts |
| [Execution register](DTD_ROADMAP_EXECUTION_REGISTER.md) | Stage status, accepted checkpoints and next action |
| [Current state](DTD_CURRENT_STATE.md) | Source/runtime evidence and unresolved DF/TD findings |
| [Invariants](DTD_INVARIANTS_AND_CONSTRAINTS.md) | Cross-project rules that every change preserves |
| [Decision register](DTD_CONFLICT_AND_DECISION_REGISTER.md) | Owner decisions, rationale and supersession |
| [Targeted matching state](DTD_TARGETED_MATCHING_PIPELINE_STATE.md) | CDR-023 cross-workflow matching target |
| [Matching completion roadmap](DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md) | M0–M10 work packages and dependencies |
| [Matching remaining criteria](MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md) | Detailed M-package acceptance checklist |
| [Decision Contract v2](specs/OWNER_TO_TRAINER_MATCHING_DECISION_CONTRACT_V2.md) | Versioned matching inputs, states, eligibility, fit, presentation and privacy |
| [R8 acceptance](R8_END_TO_END_SANDBOX_ACCEPTANCE.md) | Independent integrated acceptance, inherited evidence and remaining scenarios |
| [Sandbox matrix](specs/SANDBOX_VERIFICATION_MATRIX.md) | Cross-domain verification and promotion procedure |
| [Acquisition](specs/ACQUISITION_AND_INGESTION.md) | Source rights, statutory verification, lifecycle and capability provenance |
| [Matching and ranking](specs/MATCHING_AND_RANKING.md) | Decision-layer integration and directory/matching distinction |
| [Geography](specs/GEOGRAPHY_AND_CATCHMENTS.md) | Canonical localities and declared catchments |
| [Pricing](specs/MONETISATION_AND_PRICING.md) | Products, trials, inventory and refunds |
| [SEO](specs/SEO_AND_INDEXATION.md) | Publication/indexation, canonical, sitemap and robots rules |
| [Ops](specs/OPS_AND_OBSERVABILITY.md) | Exception-led operation, bounded actions, provider registry and recovery requirements |
| [Commercial strategy](DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md) | Business workflow integration, measured hypotheses and optional R13 concepts |
| [Google program baseline](GOOGLE_FOR_STARTUPS_PROGRAM_BASELINE.md) | Dated official program reference and explicit eligibility uncertainty |

## Historical evidence and restoration

Superseded plans, completed handovers, audit snapshots and dated release packets are outside the working tree. They are historical evidence, not an active reading list or implementation authority. Their exact originals also remain in [Git at the pre-cleanup checkpoint](https://github.com/carlsuburbmates/dtd/tree/1a0b0ff0cdffaeb753dc6ae53e0ef09ae653f188). Inspect them only for explicitly requested historical research; current contracts and the latest safe recovery requirements govern actions.

The owner's external documentation archive contains original files, a per-path disposition ledger, source commit/blob IDs, SHA-256 hashes and restoration instructions. The ledger stays outside this public repository and contains no credential values. Restore only an explicitly required historical file for research; do not reinstate obsolete instructions as current policy.

## Maintenance

Update the owning document first, then repair affected references and this map. Keep current evidence, approved target requirements and optional hypotheses clearly labelled within their owning documents. Record unresolved implementation findings in current state and owner decisions in the decision register. Remove verified resolved entries from the live open-findings list; Git preserves their audit trail. Archive superseded material outside the working tree after preserving unique knowledge and verifying the archive. Do not create duplicate plans, handover stubs or a second finding ledger.
