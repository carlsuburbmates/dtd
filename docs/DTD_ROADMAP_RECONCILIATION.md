# R0–R13 Roadmap Reconciliation

**Evidence date:** 20 October 2026. The supplied end-to-end roadmap is strategic coordination. Existing AGENTS, invariants, CDR decisions, specifications, current-state findings and matching contracts remain the implementation authority. The old completion plans remain domain checklists; no policy or closure condition is silently redefined.

| Stage | Baseline disposition | Evidence / dependency | Reconciliation action |
|---|---|---|---|
| R0 | **DONE** — exact accepted code SHA | `1ac4138e4d82991501139298cc624be732661119`; accepted Checkpoint 1 and CI run 39240506209. This does not equal runtime acceptance. | Preserve; no wholesale re-audit. New code gets its own delta review. |
| R1 | **PARTIAL (ingestion activation BLOCKED)** | DF-043 patch is independently accepted/deployed; live bounded fixtures suppressed both identities. DF-042 web identity and API-backed flow passed. Remaining applicable SR/CF runtime scenarios and rollback-to-known-good remain `NOT_VERIFIED`/`PARTIAL`. | Continue bounded R1 runtime scenarios and verify exact source/image and rollback. Keep Scheduler paused until separate R4 DF-044/045 closure. |
| R2 | **NOT_VERIFIED** | `main`/`origin/main` at `d83c7f4`; accepted branch six commits ahead; PR #12 remains open/dirty. Governance and roadmap absent on main. | After R1 exit, reconcile branch/CI/docs with reviewed ancestry, avoid force push and preserve Clerk deletion. |
| R3 | **PARTIAL** | DF-042 web identity remediation DONE; DF-046 telemetry remains OPEN; current API rollback target is available but not a proven accepted baseline. | Retain identity evidence; correct health telemetry and document rollback limits. |
| R4 | **PARTIAL (scheduler activation BLOCKED)** | DF-043 suppression DONE; DF-044 URL approval and DF-045 robots policy gaps remain; DF-026 corpus completeness partial. DF-045 is a direct scheduled-fetch safety dependency. | Close acquisition controls, review the exact delta and verify source scope before ingestion scheduler activation. |
| R5 | **PARTIAL** | DF-030 revisit authorization defect; DF-021 partial contract evidence; DF-041 public submission success path unverified. | Complete owner/trainer lifecycle and accurate communication without assuming existing render tests prove protected success. |
| R6 | **PARTIAL** | Matching contract and October M9 parity evidence exist; current health events do not show matching outage. Full latest matching and urgent-provider status not freshly proven. M0 stays DONE. | Reuse accepted artifacts; scope new checks to current changed runtime and existing DF/M criteria. Keep paid-neutral and urgent safety contracts. |
| R7 | **PARTIAL** | Ops Phases 1–5A historical sandbox acceptance preserved; DF-029 developer engine tick DONE; exact support reply/close and contact failure presentation remain targeted gaps. | Do not restart Ops remediation; attach support and communication gaps to existing IDs after ledger lookup, with affected workflow tests only. |
| R8 | **OPEN** | Integrated supply → claim → match/fallback → protected enquiry → notification → Ops resolution → cleanup acceptance not complete. | Compose existing M9 and domain scenarios after R4–R7 dependencies; produce one integrated evidence bundle. |
| R9 | **NOT AUTHORIZED / OPEN** | No production release authority granted by this task. Production remains separate from sandbox acceptance. | Preserve production isolation; execute only at the existing owner gate. |
| R10 | **OPEN** | No measured real marketplace outcome evidence in this audit. | Observe consented owner/trainer value and local supply after appropriate release; set thresholds from evidence. |
| R11 | **OPEN / separately gated** | Existing price contracts remain; no new billing activation authority. | Preserve A$0/A$19/A$149 annual/A$39/A$199 contracts and separate live billing gate. |
| R12 | **OPEN** | No sustained cost, retention, support burden or owner-time baseline established here. | Measure real operation over an approved observation window; do not invent success thresholds. |
| R13 | **OPTIONAL / SUPERSEDED as launch requirement** | Explicit roadmap says expansion is optional and evidence-triggered. | No action until demand, rights, capacity and owner decision support it. |

## Old-plan reconciliation

- `DTD_FULL_PROJECT_COMPLETION_PLAN.md` continues as the existing operational completion plan; its work packages should be mapped into R stages, not copied into a parallel replacement.
- `DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md` and `MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md` remain the matching-specific execution authority. M0 is still `DONE` at the accepted local contract/fixture baseline; M1–M9 remain individually scoped by their recorded status. The current data does not justify restarting M0 or all matching work.
- DF findings remain in `DTD_CURRENT_STATE.md`; roadmap R stages are navigation/sequence, not a second issue tracker. New DF-042–DF-048 are recorded in the current state with evidence and next actions; DF-042 and DF-043 are closed from the live open-finding list after verification.
- Existing CDR product and security decisions prevail. The roadmap does not grant production, billing, credential, new-source, destructive-data or material privacy authority.
- Old claims that the developer runtime is at revision `00021-dfd` / `00038-s6w` are historical and superseded by the 20 October live refresh; this does not alter the past acceptance evidence those entries record.

## Evidence and state vocabulary

`DONE`, `PARTIAL`, `OPEN`, `REGRESSED`, `NOT_VERIFIED` and `SUPERSEDED` describe evidence at a named stage. `BLOCKED` names an external or safety dependency; it is not a substitute for finishing independent work. Engineering, product, operational and business acceptance remain separate outcomes.
