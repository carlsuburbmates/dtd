# Dog Trainers Directory — End-to-End Product & Business Roadmap

**Version:** Strategic roadmap v1.1 — commercial integration reconciled 26 October 2026; original North Star approved 20 October. Stage identifiers, accepted checkpoints and action gates remain governed.
**Starting artifact:** `dtd_remediation_release_checkpoint1_reconciled_matrix.md` (Antigravity's corrected Checkpoint 1 evidence; supplied in conversation; not asserted to be committed to GitHub)
**Frozen accepted remediation code:** `1ac4138e4d82991501139298cc624be732661119` on `fix/ops-security-integrity-d83c7f4`
**Existing implementation authority:** `AGENTS.md`, `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`, `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md`, approved specifications and applicable decision contracts.
**Existing execution sources:** `docs/DTD_ROADMAP_EXECUTION_REGISTER.md`, `docs/DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md`, `docs/MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md`, `docs/specs/SANDBOX_VERIFICATION_MATRIX.md`, `docs/DTD_CURRENT_STATE.md`.
**Status:** The owner has approved the business North Star below. This roadmap coordinates existing approved work and proposes new evidence-based *business validation stages*; it does not by itself authorise production deployment, live payments, new data sources, credentials, changes to locked policy, or irreversible actions.

## 1. North Star and definitions of finished

**North Star (owner approved):** Establish Dog Trainers Directory as a trustworthy, useful and financially sustainable dog-trainer discovery and matching service that operates predominantly through automation, with the founder responsible for meaningful decisions rather than routine administration.

DTD serves **Greater Melbourne** first. Dog owners can discover appropriate, evidence-supported trainers and make consented contact without paying DTD. Legitimate trainers can claim/correct their listings, receive relevant opportunities and optionally purchase fair, transparent visibility products. Automated workflows maintain operational truth and escalate genuine exceptions; AI advises or assists inside deterministic safety and evidence boundaries.

The North Star has **four independently assessed achievements**, not one binary software completion flag:

1. **Engineering-ready:** secure, coherent, testable, recoverable, observable implementation.
2. **Product-ready:** complete and useful owner and trainer journeys, proven with synthetic sandbox fixtures and realistic scenarios.
3. **Operationally live:** separately authorised production release with real provider/control-plane evidence, no unsupported claims and bounded owner workload.
4. **Business-validated:** measured owner value, trainer value, data quality, acquisition, retention, operating cost and founder workload over real observation windows; benchmarks set from observed baselines rather than invented now.

**Do not confuse:** implemented code, local tests, remote CI, deployed to sandbox, sandbox-accepted, deployed to production, production-observed and commercial-successful.

## 2. Scope and locked controls

- Owner browsing, matching and contacting are free; no commission, per-lead fee or per-introduction charge.
- Trainer-side pricing already approved: Core A$0; Pro A$19/month or A$149/year; Suburb Sponsorship A$39/month; Melbourne-Wide A$199/month. Active inventory/trial/refund rules are in `specs/MONETISATION_AND_PRICING.md` and require their existing separate release gates.
- Matching: deterministic eligibility, AI-assisted **paid-neutral** fit, deterministic presentation; paid status only in the approved `0.05` comparable-fit band. No unsupported capabilities, ranking manipulation or invented safety guarantees.
- Persistent trainer inventory must come from authorised first-party, official URL or licensed sources, with provenance and suppression. ABR is statutory verification, not a discovery source. Google Maps/Places is not an acquisition shortcut; M7 remains optional and gated.
- **First Leash** is a separate education app/deployment. Maintain only a privacy-safe static/query-free handoff from main DTD.
- Ops principle: **OWNER BY EXCEPTION. AUTOMATION BY DEFAULT. AI ANALYSIS WHEN NEEDED.** Ops AI is advisory; consequential actions remain authorised, auditable and idempotent. Preserve historically implemented Ops Phases 1–5A rather than reopening them without a verified regression.
- Developer sandbox: `dogtrainersdirectory-dev`, Cloud Run `dtd-api-dev` and `dtd-web-dev`, Atlas `dtd_sandbox`, test/sink email and Stripe test mode. Production is `gen-lang-client-0028123502` with its separate live MongoDB and provider state.
- Preserve repository-root `AGENTS.md` Section 6A independent review/commit gate. Do not replay historical pushes or rewrite history for procedural appearances. Production, billing, refunds, real-data deletion, policy, credentials and provider authority require their respective explicit approvals.
- Status words: **DONE** = independently evidenced at this stage; **PARTIAL** = only some requirements evidenced; **OPEN** = not evidenced/implemented; **NOT_VERIFIED** = claim exists but lacks the required independent proof; **REGRESSED** = formerly accepted guarantee demonstrably fails; **SUPERSEDED** = explicit documented replacement. Use **BLOCKED** for external dependency and name the unblock action.

## 3. Starting point: Checkpoint 1 is CLOSED

**Checkpoint 1 — Cumulative remediation code acceptance** has already been granted for immutable SHA `1ac4138e4d82991501139298cc624be732661119`, covering SR-01–SR-06, CF-01–CF-05, claim method reconciliation, fraud release and delisting protection. **Do not re-audit this package wholesale.** The accepted matrix needs only two non-blocking route-label corrections: submission approval is `POST /api/oversight/submissions/{submission_id}/review` (`review_held_submission`), and standard claim start is `POST /api/trainers/{trainer_id}/claim` (`start_trainer_claim`).

Antigravity reported clean frozen ancestry, GitHub Actions `Verify` success at run `39240506209`, Python compile pass, `PRELAUNCH_RELEASE_GATE=PASS`, 619 isolated integration tests passing, and 122 targeted Ops/claims tests passing. These are **reported execution evidence accepted for Checkpoint 1**, not a claim that this author has rerun them. The privacy erase implementation remains scoped, sequential and non-transactional; verified real erasure authority and completeness may not be inferred from synthetic tests.

**Checkpoint continuity:** R1 is DONE WITH NAMED BLOCKED FOLLOW-UPS and R2/R3 are accepted at their recorded scope. Current stage disposition and next action live in the [execution register](DTD_ROADMAP_EXECUTION_REGISTER.md); [R8 evidence](R8_END_TO_END_SANDBOX_ACCEPTANCE.md) preserves accepted SR/CF scenarios and remaining checks. Historical traffic targets are not current recovery instructions. The 25 October credential containment governs developer recovery; scheduled ingestion remains PAUSED under its R4 activation gate.

## 4. Roadmap at a glance

### How to use this roadmap

This document defines the **destination, stage outcomes and dependencies**. Use the linked records for the changing execution details:

- [DTD_ROADMAP_EXECUTION_REGISTER.md](DTD_ROADMAP_EXECUTION_REGISTER.md) — current stage status, next authorised action and review checkpoint.
- [DTD_CURRENT_STATE.md](DTD_CURRENT_STATE.md) — current implementation evidence and open DF/TD findings.
- The stage contracts in §5 — what must be demonstrated to complete each R stage.
- [DTD_CONFLICT_AND_DECISION_REGISTER.md](DTD_CONFLICT_AND_DECISION_REGISTER.md), approved specifications and `AGENTS.md` — binding decisions and controls.

The groupings below are navigation aids only. They add no gates, change no dependencies and do not replace the existing finding or decision records.

| Horizon | Stages | Outcome |
|---|---|---|
| **1. Preserve and prepare** | **R0–R3** | Keep the accepted baseline intact, verify and consolidate the sandbox release, then establish a recoverable release foundation. |
| **2. Build the trustworthy marketplace** | **R4–R6** | Maintain authorised, current trainer supply; complete owner and trainer journeys; prove safe matching and urgent-support behaviour. |
| **3. Operate and validate** | **R7–R12** | Accept operational workflows, prove the integrated product, pass separate release gates, then measure marketplace value, commerce and sustainable operation. |
| **4. Evolve only on evidence** | **R13** | Consider expansion only after the core business outcomes are evidenced and the owner approves a specific opportunity. |

**Current pointer (26 October 2026):** R0–R3 remain accepted. PR #20 integrated independently reviewed source `79b8165` as `4e54968`, followed by source/Git consolidation and the separately approved 25 October developer credential containment. This closes source consolidation and the scoped credential/flag findings, not the corrected R4–R8 runtime matrix. The containment reused the prior image; do not infer current-main deployment from it. Use `DTD_CURRENT_STATE.md` for exact source/runtime and recovery evidence. The commercial plan now forms one mapped business workflow inside R0–R13 under CDR-028. Production R9 and live commerce R11 remain separately gated.

### Stage status and expected outcome

| Stage | Name | Current evidence state (see live execution register) | End-of-stage deliverable / required state | Dependency |
|---|---|---|---|---|
| **R0** | Remediation Checkpoint 1 | **DONE — accepted code** | Immutable accepted SHA + reconciled SR/CF matrix + reported preflight/CI evidence | Established |
| **R1** | Controlled remediation sandbox release | **DONE WITH NAMED BLOCKED FOLLOW-UPS** | Scenario outcomes and cleanup are accepted in `R8_END_TO_END_SANDBOX_ACCEPTANCE.md`; remaining follow-ups retain R4/R5/R7 assignments; the R3 recovery checkpoint is recorded in `specs/OPS_AND_OBSERVABILITY.md`. Scheduled ingestion remains PAUSED under the R4 activation gate. | R0 |
| **R2** | GitHub, docs and remediation cleanup | **DONE** | PR #12 and safety follow-up #15 are merged; reconciliation, exact sandbox identity and remaining findings are in `DTD_ROADMAP_EXECUTION_REGISTER.md`. Later R3 integration has its own exact-delta review and safe-deployment checks. | R1 disposition and separate governance review |
| **R3** | Platform/release foundation | **DONE — developer checkpoint** | Accepted PR #17/#18 integrate DF-046 and dependency corrections; main `48f68f4` CI/graph passed and zero Dependabot alerts remain. Cloud Run identity, bounded recovery and retired Vercel connection are verified; CDR-027 supersedes DF-053. Provider follow-ups retain R4/R7/R9 ownership, with credential/scanner uncertainty explicitly tracked. | R2 |
| **R4** | Trustworthy trainer supply | **PARTIAL** | Authorised-source intake/rerun, match-ready declaration/projection, freshness, correction, suppression and indexes verified end to end; verify DF-051 acquisition dedup behavior before scheduler activation | R3, existing M0 |
| **R5** | Owner and trainer-facing journeys | **PARTIAL** | Browser-tested mobile/desktop entry → questionnaire/result/profile → protected enquiry; trainer claim/edit/correction journey; accessibility and truthfulness | R3, R4 where supply needed |
| **R6** | Matching, fairness and urgent support | **PARTIAL** | M0–M6 and M8 applicable criteria DONE; AI/fallback parity; safety, fairness, weak-supply, urgent and follow-up states; M7 explicitly optional | R4–R5 |
| **R7** | Ops and communications operational acceptance | **PARTIAL — candidate audit failed; historical acceptance retained at its scope** | Representative owner cases trace UI → API → persistence → notification/recovery → `/ops`; owner by exception; verify one controlled developer Monitoring alert receipt through an approved sink or the configured owner channel; no wholesale redesign | R4–R6 |
| **R8** | Integrated product sandbox acceptance | **PARTIAL — corrected runtime acceptance pending** | Existing M9 + DTD-wide acceptance; synthetic end-to-end owner/trainer and error paths; clean data; independent product release verdict | R3–R7 |
| **R9** | Production promotion (separate gate) | **NOT AUTHORISED for new release** | Owner-authorised zero-traffic canary, recovery/smoke, controlled routing; post-release monitoring; **billing remains off** | R8 + specific authority |
| **R10** | Real marketplace validation | **NOT YET MEASURED as this roadmap** | Permissioned real owner/trainer activity and consistent privacy-bounded funnel, outcome, satisfaction, supply and support measurements | R9 / approved current live posture |
| **R11** | Commercial activation and validation | **GATED** | Approved no-charge tests first; separately approved Stripe live activation, entitlements, trial anchor, sponsor inventory, refunds/portal; observed willingness to pay and retention | R9–R10 + explicit billing authority |
| **R12** | Sustainable exception-led operation | **FUTURE BUSINESS-OUTCOME GATE** | Demonstrated continuing value, adequate unit economics, dependable data freshness and manageable founder workload over agreed observation windows | R10–R11 |
| **R13** | Evidence-triggered evolution (optional) | **VISION ONLY** | Owner-approved expansion only when explicit trigger and cost/benefit evidence exist | R12 + new decision |

**Ordering is dependency-based, not an instruction to repeat tests already valid for unchanged code.** Historical Ops phase acceptance and M0 DONE are carried forward. Mark every older claim as independently confirmed, stale, PARTIAL or not relevant, rather than automatically revoking it.

### Commercial workflow integrated into these stages

At the owner's direction in the 23–24 October Antigravity discussions, the [commercial strategy](DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md) refines this roadmap; it does not create a second execution track. The intended production journey is useful local discovery → eligible paid-neutral matching → explicit consented contact → truthful notification and trainer participation → free claim/capability management → optional, separately authorised Pro/sponsorship → measured value and sustainable owner workload.

| Business engine | Existing R stages | Contract to preserve |
|---|---|---|
| Local discovery and suburb SEO | R4 supply; R5 website/indexation; R8 connected proof; R10 outcomes | Existing `/melbourne/:suburb` route, real supply/content eligibility, accurate structured data; no promised search ranking or zero acquisition cost. |
| Guided matching and useful owner contact | R5–R6; R7 delivery; R8 connected proof | Current v2 eligibility/AI/fallback/urgent contract, 0.05 presentation band and explicit enquiry consent; no automatic lead broadcast from a match result. |
| Free trainer claim and optional Pro trial | R4–R5 facts/session; R7 notifications; R8 safe proof; R11 live commerce | Free/Core enquiries remain free. Eligible trial starts on authorised Stripe subscription creation, not on claiming alone; day-23 warning, cancellation and failure truth remain required. |
| Sponsorship and business sustainability | R6 presentation; R8 safe inventory proof; R11 commerce; R10/R12 measurement; optional R13 | Two sponsors/suburb, four suburbs/business default, paid-neutral fit, genuine availability and provider-backed inventory; no guaranteed top placement, margin, financing or expansion. |

The present release goal is the integrated production service after the final sandbox/owner audit and R9 authority. The Google re-review describes a demonstrable MVP and a funding direction; it does not certify all live workflows, award credits, or activate R11. Cost, revenue, workload, valuation and fundraising examples remain hypotheses until measured/reviewed at their assigned stages. R7 remains Ops/communications; SEO is included through existing website/indexation and integrated acceptance work.

## 5. Stage-by-stage execution and exit contracts

**Accepted evidence:** retain scoped R0–R3 acceptance from the execution register. R4–R8 corrected runtime proof remains partial. Use the [R8 named scenario matrix](R8_END_TO_END_SANDBOX_ACCEPTANCE.md#named-srcf-follow-ups-retained-for-r8) for the accepted SR/CF subcases and exact remaining checks; do not restart completed code remediation or infer provider delivery from a synthetic event.

### R0 — Remediation Checkpoint 1: preserve the accepted baseline

**Status:** DONE. **Inputs:** corrected Checkpoint 1 finding matrix; exact commit; six-commit lineage; test/CI handoff. **Deliverables:** immutable candidate reference, source/test/CI evidence index, SR/CF code-acceptance register, known scoped limitations. **Exit:** already granted. Do not change release SHA to fix prose; preserve code acceptance unless an actual confirmed regression is discovered.

### R1 — Promote and certify the accepted remediation in the developer sandbox

**Execution:** Verify deployment script effects, latest live revisions, exact image-to-commit provenance, secret reference roles, sandbox DB and recipient containment, disabled commercial/recovery flags, rollback target. Resolve necessary cloud authentication via trusted local UI only. Use the approved sandbox release process for the exact independently accepted SHA. Any IAM or scheduler change must remain within explicit owner authorization and its named developer scope; production remains untouched. Run relevant checks from `specs/SANDBOX_VERIFICATION_MATRIX.md` for the affected release paths.

**Required sandbox scenarios:** signed/unsigned/replayed Resend webhook and idempotency; held trainer approval, suppression, duplicate/canonical builders; legitimate sandbox OTP claim, invalid/expired/conflict/exceptional review; support intake/reply failure/dedup/concurrency/closure; unverified privacy scrub 403 without mutation; fraud release and delisting; durable obligations, positive terminal resolution, read-only oversight zero writes; `/ops` auth/audit and basic UI compatibility. Use only uniquely namespaced synthetic data and provider-safe sinks. Do not assert a simulated person accepted real terms; do not execute destructive real-data privacy actions.

**Deliverables:** record exact revision/image/source, before/after traffic, sanitised configuration, safe recovery disposition, scenario-level UI/API/data/audit/provider evidence, fixture absence and restored temporary settings in the existing R8 acceptance record. Historical accepted R1 packets remain in Git; do not create replacement R1 files. **Exit:** all applicable agreed Stage 2 runtime gates PASS, or specific named BLOCKED items remain without a false completion claim.

### R2 — Consolidate GitHub, documents, and remediation artifacts

**Execution:** Recheck main HEAD/ancestry, verify no intervening commits are lost, use repository-governed merge/fast-forward after review and sandbox gates, ensure CI green on resulting `main`; do not force-push. Correct the two route labels in the handoff. Update existing authority docs rather than generating redundant documents: `docs/DTD_CURRENT_STATE.md` (dated exact SHA/revision/CI/sandbox evidence, remaining DF findings), `docs/DTD_ROADMAP_EXECUTION_REGISTER.md` (latest baseline and next active work), `docs/README.md` only if navigation/summary drift, and targeted Ops/sandbox specs only for actual contract changes. Preserve closed history in Git, remove only safe disposable local scratch artifacts and synthetic sandbox fixtures. Keep real records, unique branches and security audit trails.

**Deliverables:** the execution register records accepted source/main SHA and scoped checkpoint; current state owns latest runtime/recovery and open findings; R8 owns inherited scenario outcomes and cleanup scope. Historical full packets remain recoverable from Git and the external archive. **Exit:** one truthful `main` baseline, live sandbox alignment, no contradictory active SR/CF claims; remediation workstream marked CLOSED with exact scope. *This is a workstream closure, not DTD product completion.*

### R3 — Reconcile remaining platform/release-safety blockers (existing Phase 0–1)

**Execution:** Carry forward already completed sandbox IAM and reproducible local tests. Reconcile existing DF-006, DF-009, DF-010, DF-012/013, hosting/DNS DF-001/007 and provider recovery evidence against the latest SHA. Verify current CI/build/dependency state and minimal low-cost recovery procedure. Treat production hosting changes, credential changes and provider provisioning as separately gated. Sentry/first-party attribution only within approved privacy, cost and deployment boundaries. Use the owner-confirmed Cloud Run developer sandbox under CDR-027. Firebase Hosting is production-only; the inferred developer Hosting requirement DF-053 is superseded. Do not use production Firebase defaults. The Monitoring alert policy and attached email channel must be enabled and recorded with recovery ownership; actual delivery receipt is R7 communications evidence because its test would send a real owner notification. Assign Atlas/ABR recovery controls to R4, Resend/Sentry and owner-notification delivery to R7, Stripe management to R9, retaining DF-001/DF-050 as applicable. Do not redo accepted independent provider tests unless configuration changed.

**Deliverables:** current deployment/recovery runbook; provider dependency registry with safe references and last successful check; CI/dependency audit manifest; hosting/SEO risk inventory; DF closure/defer matrix. **Exit:** release pipeline repeatable, controlled and observable; sandbox target is identified; safe default-branch integration is independently accepted; blockers are fixed or explicitly assigned to a later R with owner-authorized rationale. Configured Monitoring policy/channel evidence satisfies the R3 configuration checkpoint; delivery receipt remains an explicit R7 requirement.

### R4 — Trainer supply, acquisition, freshness and trainer control (existing Phase 2 + M1)

**Execution:** Establish lawful approved-source/consent basis, controlled namespaced ingestion and idempotent rerun; distinguish public profile facts from validated *match-ready* capability declaration. End-to-end verify trainer self-submission, claim, structured confirmation, update/correction, contact readiness, suppression and removal. Persist field-level basis, timestamps, source rights and freshness/invalidation; ensure ABR checks statutory status, not discovery. Avoid claiming 539 suburbs equals 539 available trainers; canonical suburb catalogue is geography only. Verify adequate target-area capacity using evidence rather than arbitrary profile count. Investigate DF-014, DF-026 and relevant related findings.

**Deliverables:** source-authority manifest and approved run plan; before/after ingestion/rerun ledger; declared-capability schema and freshness/invalidation report; duplicate/suppression/claimed protection evidence; representative trainer self-service screenshots; `/ops` exceptions and cleanup. **Exit:** M1 criteria and relevant acquisition contracts pass in sandbox; only current validated capacity is matchable. Real licensed sources or production ingestion still require their separate approval.

### R5 — Owner journey, website and trainer self-service (existing Phase 3 + M2/M5 UI)

**Execution:** Complete the already recorded final browser-submitted protected-enquiry acceptance in safe sandbox conditions; do not equate mock submission or fabricated consent with a real user's authority. Verify entry/navigation, config outage, form validation, consent, privacy-safe result/profile handoff, enquiry release and truthful confirmation, keyboard/accessibility/mobile viewports, metadata/SEO/sitemap eligibility, corrected claim-session restoration and trainer capability management. Keep First Leash separate via query-free static link. Reuse existing responsive/browser evidence unless affected assets changed.

**Deliverables:** mobile/desktop browser journey matrix and captures; UI/API/DB/notification/ops proof; authenticated trainer manage-listing flow; consent/URL/redaction evidence; SEO canonical and noindex/sitemap checklist; issue list only for demonstrated regressions. **Exit:** owner and trainer can complete the relevant ordinary paths, failure states are clear, no private behaviour in URLs, and the defined frontend acceptance cases pass.

### R6 — Matching, safety, AI/fallback and urgent-support acceptance (existing Phase 4 + M0–M8)

**Execution:** Preserve **M0 DONE**, do not restart Decision Contract v2. Work from `docs/MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md`, completing M1–M6 and M8 at their existing required scope; M7 Maps/Places remains optional and disabled unless separately authorised. Demonstrate deterministic eligibility before AI, source/freshness gates, paid-neutral fit, exact 0.05 presentation, broadening only with disclosure, no-match and weak-evidence states, Gemini/deterministic parity, degraded cases, consent and follow-up. Verify urgent routes and official provider freshness/correction without inventing clinical advice or persisting Places data. Prior live M9 and parity cases remain supporting evidence; fill only unresolved gaps and configuration drift.

**Deliverables:** versioned scenario/fixture matrix with reason codes and expected responses; AI/fallback parity report; provenance/freshness test set; safety/urgent and thin-supply cases; privacy/0.05 anti-gaming tests; `/ops` exceptions, notifications/retry evidence; M0–M8 status register. **Exit:** all mandatory M0–M6, M8 acceptance clauses satisfied; M7 DONE if enabled or explicitly disabled; no material matching PARTIAL/REGRESSED items concealed.

### R7 — Ops + transactional communications operational acceptance (existing Phase 5)

**Execution:** Retain implemented historical Ops Phases 1–5A, simple three-tier owner UI, 14-domain coverage and advisory-only AI analyst. Check only affected integration boundaries and unresolved DF items. Execute representative nontechnical owner workflows in sandbox: approve/hold trainer, dispute/dedupe/delist, answer customer enquiry/complaint, handle claim conflict, notification failure/retry, operational backlog, provider/scheduler outage and recovery. Confirm user-visible impact, safe next action, accurate persisted result, audit and exception clearing. Keep self-healing production-disabled; no automated refunds or credential mutation. Demonstrate a real owner-responsibility queue without requiring developer intervention for routine business decisions.

**Deliverables:** owner action taxonomy/status map; operator walkthrough (mobile/desktop where changed); failed-email and provider-recovery drill records; `/ops` evidence, AI-advisory logs, alert route/recovery/coverage matrix; quantified human action count from scenarios. **Exit:** intended Ops workflows are operable, truthful, bounded and exception-led; prior completed UI phases are not reclassified incomplete simply because the cumulative remediation changed backend routes.

### R8 — One integrated developer-sandbox product acceptance (existing Phase 6 + M9)

**Execution:** Run the master end-to-end journey with isolated owned fixtures: authorised trainer data → match-ready capacity → mobile owner input → triage/eligibility → AI/fallback result → profile → consented protected enquiry → notification (or simulated failure) → opt-in follow-up → `/ops` case/verified recovery → complete fixture teardown. Check no-current-supply, unsafe/urgent, suppression, expiry, provider outage, privacy, idempotency and escalation cases. Incorporate the existing matching M9 matrix; do not conflate a passing health check with completion. Screen-reader/keyboard/mobile captures required for affected screen paths.

**Deliverables:** `R8_END_TO_END_SANDBOX_ACCEPTANCE.md` with case-by-case evidence, commit/revisions, UI captures, DB/notification/Ops records, safe external-provider proof, verified zero-trace cleanup, independent Codex audit outcome, and any deferred owner-gated item. After R8 acceptance, hand the complete developer sandbox and evidence packet to the owner for the owner's audit. **Exit:** applicable full product contract independently accepted in the developer sandbox and owner audit handoff is complete. This authorises no production change by itself.

### R9 — Controlled production release (existing Phase 7 + M10; explicit owner gate)

**Execution:** Start only after R0–R8 are complete, the owner has audited the final developer sandbox, and the owner grants specific authority for source SHA, environment, traffic progression and any separately gated provider/config/data mutations. This roadmap stage is not standing production approval. Do not silently enable Stripe live checkout, refunds, self-healing, new licensed acquisition, credential rotation or scheduler modifications. Preflight Cloud Run/Firebase routing, backups/rollback, secrets/permissions, database/retention, monitoring/edge alerts, privacy/SEO truth, domain compatibility and no-charge billing. Use zero-traffic canary as permitted, smoke the tagged revision, advance traffic only after measured results, and monitor recovery/rollback readiness.

**Deliverables:** owner-approved release manifest, tagged revision/image, zero-traffic canary and smoke/rollback evidence, live monitoring dashboard, current-state/deploy log and post-release health report. **Exit:** authorised integrated code live with no critical regressions; payments remain disabled unless separately approved. **Do not claim market validation from this gate.**

### R10 — Prove real owner/trainer marketplace value

**Execution:** Establish ethical, permissioned real-world pilot/observation after or within separately authorised safe live traffic. Measure discovery to useful contact, owner understanding of reasoned matches, quality/relevance of trainer leads, trainer response/participation, consented follow-up outcomes, unmet local demand, source freshness, support complaints and drop-offs. Use minimal privacy-bounded events and voluntary qualitative feedback; avoid storing dog behavioural dossiers for analytics. Start with a small tractable Greater Melbourne segment rather than claiming universal coverage. Set actual success thresholds **after** observing baseline and owner approving decision rules, not as invented commitments.

**Deliverables:** measurement dictionary/event provenance and consent map; first observed baseline report by cohort/area; owner and trainer feedback summary; qualified-enquiry and fulfilment funnel; supply-demand gap map; evidence-led product prioritisation; pilot continue/adjust/stop decision with rationale. **Exit:** demonstrable useful owner/trainer interactions and a trustworthy method for measuring them. If outcomes are weak, make one bounded experiment tied to evidence—not a speculative platform rebuild.

**Commercial strategy alignment (planning only):** Validate a customer-funded Greater Melbourne model before treating institutional fundraising or geographic expansion as a plan. Record trainer acquisition, useful enquiries, willingness to pay, conversion, churn, support burden and fully loaded provider costs as hypotheses until observed. The illustrative targets and funding scenarios in `DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md` are not approved thresholds, forecasts, product commitments or evidence; replace or retire them as R10/R12 data arrives. This strategy creates no execution authority and does not advance R9 or R11.

### R11 — Commercial activation and proof of trainer value (separate live-billing gate)

**Execution:** First complete no-charge Stripe provider testing and public copy/terms/refund/entitlement verification. After separate owner billing authority, activate only approved trainer-side products and cohort trial anchor together, validate checkout/webhook/idempotent subscription entitlements/sponsorship inventory, cancellation/portal, day-23 notice, refund review, failure/recovery and Ops audit. Preserve A$0/A$19/A$39/A$199 and A$149/year contracts. Use observed trainer engagement and willingness-to-pay evidence rather than pretending launch guarantees demand.

**Deliverables:** controlled billing activation record, approved terms/version and `STRIPE_LIVE_ANCHOR_AT` evidence (without secrets), full checkout-to-Ops test, no-double-trial/inventory/refund safeguards, pricing truth audit, subscription/payment/retention reporting and cost ledger. **Exit:** commerce safely operable under granted authority, paid trainer value and payment outcomes measurable; no owner lead fees or fit distortion.

**Funding boundary:** Google for Startups Start-tier eligibility and any cloud credits are separate from Stripe/live-billing authority. Do not represent credits as approved or guaranteed, and do not activate a trial cohort or live checkout as part of roadmap alignment.

### R12 — Demonstrate a sustainable owner-by-exception operating business

**Execution:** Track rolling outcomes: active/accurate supply, local coverage gaps, owner-to-contact completion, useful enquiries, trainer repeat engagement, conversion/retention/churn, revenue and sponsor utilisation, refunds/complaints, provider/cloud/AI/SMS/email costs, monitoring incidents, automation recovery and time the founder spends on routine work. Categorise owner interventions as necessary business decisions versus preventable technical chores. Create simple weekly/monthly summaries in Ops; warn only at owner-approved thresholds. Set thresholds using observed baseline and cost requirements, then evaluate at agreed time windows (e.g. two consecutive reporting periods **if approved**, not automatically).

**Deliverables:** KPI definition/ownership source-of-truth, privacy-safe operational and financial dashboard, observed baseline and approved thresholds, repeat-period performance report, intervention/incident burden analysis, runbook/delegation plan, specific retention/growth experiments and go/adjust/hold decision. **Exit:** sustained useful owner/trainer outcomes, finances covering owner-approved viability threshold, acceptable founder workload and dependable recovery over observed time—not just successful tests. If not met, maintain an explicit improvement backlog; technical product completion remains separately recognised.

**Capital-readiness alignment:** Any later angel or venture discussion should use measured R10–R12 evidence and a separately reviewed legal/entity and financing plan. No funding amount, valuation, incorporation date, investor approach or national rollout is committed by this roadmap entry.

### R13 — Optional evidence-triggered expansion

**Status:** not a launch requirement. Based on `docs/DTD_COMMERCIAL_SCALING_AND_FUNDING_STRATEGY.md`, candidate expansions (new geography, licensed feeds, plan types, partner/First Leash distribution, richer analytics/AI, additional products) require measured demand, rights, financial and maintenance capacity, owner decision and updated contracts. **Deliverable:** opportunity/evidence proposal and approval record. **Exit:** only approved experiments are implemented; otherwise preserve stable Greater Melbourne service and do not reopen completed work.

## 6. Dependency map and parallelism

```text
R0 accepted Checkpoint 1
  -> R1 sandbox deploy and scoped runtime acceptance
  -> R2 main / authoritative docs / remediation closure
      -> R3 release foundation and current DF reconciliation
      -> R4 lawful trainer supply ----+
      -> R5 owner/trainer journeys --+--> R6 matching and urgent-support contracts
                                      -> R7 Ops and communications acceptance
                                      -> R8 integrated M9 sandbox gate
                                      -> R9 authorised production code promotion (M10)
                                      -> R10 real marketplace value observation
                                      -> R11 separately authorised commercial activation
                                      -> R12 sustainability and low-owner-load evidence
                                      -> R13 optional owner-approved growth
```

Read-only discovery, UI research and existing evidence consolidation may overlap safely. Mutations and dependent acceptance cannot be marked DONE before prerequisites. R7 existing historical Ops phase evidence is carried forward, not rebuilt. The platform is already publicly reachable; R9 concerns promotion of the **new verified release**, not a claim this is the first public launch.

## 7. Stage acceptance packet — same schema every time

Each stage returns exactly these four evidence sections (avoid endless standalone audit reports):

1. **State transition:** stage ID, base/HEAD SHA, environment/revision, `BEFORE → AFTER`, status, owner decision gate.
2. **Acceptance evidence:** contract/finding/M IDs, exact commands and provider/browser evidence, expected vs observed results, persisted/audit state, adverse cases, privacy/security restrictions and test limitations.
3. **Reconciliation and cleanup:** Git/docs changes, temporary fixture IDs and verified removal, settings restored, evidence retained, open findings and known nonblocking limitations.
4. **Next step:** **one** next authorised package with precise dependencies, outputs and completion rule; do not manufacture new prerequisites unrelated to that stage.

No manual duplication of DONE statuses across many files. `docs/DTD_CURRENT_STATE.md` is the live factual register; project completion plan coordinates; matching roadmap holds M IDs; specifications define contract; decision register only records actual decisions. Historical audit documents remain history, not competing truth.

## 8. Owner decision gates (no unnecessary approvals)

| Gate | Owner choice truly required | Not required |
|---|---|---|
| R0–R2 | New material authority if discovered; otherwise accepted remediation/sandbox work can proceed per AGENTS.md | Reapprove the same analysis or plan |
| R4 | New official URLs/licensed sources or material source-rights decisions | Each non-destructive read-only scan |
| R6 | New decision-contract/policy version or optional M7 enablement | Reapprove existing matching policy |
| R9 | Production SHA/traffic release and separately gated config/data/credential actions | Re-run previously accepted local tests with unchanged code merely for reassurance |
| R10 | Real-world pilot consent/recruitment model and observed success thresholds when evidence is available | Invent benchmarks prematurely |
| R11 | Live charging, trial anchor, refund execution and financial/legal terms where not already authorised | Equate Stripe test-mode configuration with permission to charge |
| R12–R13 | Sustainable-business thresholds and substantive expansion decisions | Routine exception-led observation/reporting |

## 9. Measurement ladder — outcomes, not vanity counts

**Owner usefulness:** share of consented, valid owner journeys reaching an appropriately explained state; result-to-profile and profile-to-protected-enquiry completion; confirmed owner/trainer contact, where observable; opt-in feedback on relevance; safety/complaint and abandonment signals. **Not** just pageviews or model completions.

**Trainer value:** eligible active claimed listings, current match-ready capabilities, relevant enquiries, acknowledged/answered contacts, corrections processed, trainer satisfaction/renewal; distinguish unpaid vs paid without biasing raw matching fit.

**Marketplace integrity:** lawful/attributable source coverage, freshness and correction turnaround, actual suitable-trainer coverage by suburb/need, opt-outs/suppressions honoured, invalid/fabricated claim rate, SEO indexed pages only where eligible.

**Reliability and independence:** successful/failed notification state with receipts, recovery time and backlog age, provider/AI degradation visibility, percentage of routine cases auto-resolved with verified evidence, substantive owner decisions per period, avoidable manual technical interventions and owner time.

**Economics:** paid trainer count and retention, monthly recurring revenue, refunds, sponsor occupancy, paid conversion with consent and terms, cloud/provider spend, incremental service/support costs, cost per *useful* enquiry where measurable, positive operating contribution after agreed costs. No forecasts presented as facts.

Establish event definitions, denominators, observation window, consent/privacy limits and baseline coverage before adopting numerical targets. A KPI cannot be considered demonstrated if its underlying event is not verifiable or the denominator is unknown.

## 10. Final objective and closure declarations

- **Remediation CLOSED:** R1 + R2 finished after previously accepted R0; no general re-review of Ops phases. This closure is bounded to the 2026 remediation package.
- **Product SANDBOX-READY:** R0–R8 applicable contracts independently accepted in the current developer sandbox, M0–M6/M8/M9 DONE and M7 optional/disabled; the complete evidence packet is ready for the owner's audit. Production promotion remains a separate R9 gate after owner audit and specific authority.
- **Integrated RELEASE DEPLOYED:** R9 approved and live monitored. Production deployment is not live commerce authorization.
- **MARKETPLACE VALUE VALIDATED:** R10 evidenced with genuine permissioned user/trainer observations.
- **COMMERCE VALIDATED:** R11 safely activated when separately approved and supported by actual value/economics, not merely a configured Stripe client.
- **ULTIMATE GOAL EVIDENCED:** R12 satisfies explicit, observation-based and owner-approved customer value, trainer value, financial sustainability and owner-by-exception thresholds. This is ongoing measurable evidence, not an assertion of perfection or a one-time forever certification.
- **EXPANSION:** R13 only when evidence and owner consent warrant it.

**Immediate executable next instruction (23 October 2026):** correct the independently reproduced R4 DF-044/045/051 failures, then the bounded R5/R7 failures identified in the R8 audit. Obtain exact-SHA independent code acceptance before remote/developer-sandbox advancement; complete missing runtime acceptance under existing stage exits. Retain source-authority and provider credential/recovery checks and keep ingestion PAUSED. R0–R3 remain accepted; production and live billing remain separately gated.
