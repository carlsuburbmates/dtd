# AI/LLM/Agent Session Execution Standards

This file defines how any AI, LLM, agent, bot, automated assistant or AI-enabled tool must execute work in this repository, regardless of provider, interface or task context. Platform-specific paths such as `.codex/` identify available tooling; they do not limit these rules to Codex.

## AI Capability Utilisation Rule (`LOCKED`)

All tasks must actively consider relevant available AI-native capabilities where useful, including:

- skills
- subagents
- plugins
- browser/visual inspection tools
- repo analysis tools
- test/build tooling
- available MCP/app integrations
- project-specific reusable workflows

The acting AI system must not default to manual text editing when a more suitable native capability is available.

## Evidence-first owner-assistance rule (`LOCKED`)

DTD is a solo-operator project. Any AI system entering or operating in this repository must reduce unnecessary human overhead by investigating before asking the owner to decide.

1. Inspect the repository, current configuration, relevant provider state, existing decisions and available evidence before asking the owner to choose a value or direction.
2. State verified facts, uncertainty, risks and a recommended path. Where a safe, reversible and in-scope default is supported by evidence, use it rather than presenting the owner with an arbitrary choice.
3. Carry forward the owner's authorisation from the current and earlier turns until it is revoked or the scope changes. Ask only when the next action needs authority not already granted for a material financial, security, legal, privacy, production, product-scope or irreversible change, or when evidence cannot resolve a required choice.
4. Do not ask the owner to invent thresholds, settings or architecture choices before measuring the current state. If a decision gate remains, explain exactly what is missing, why it matters and the smallest decision required.
5. Prefer exception-driven operation and one focused decision gate over repeated broad clarification requests. This rule applies to every AI, LLM, agent, bot, assistant, plugin or automated workflow operating in the project.

## DTD North Star and end-to-end roadmap (`OWNER-APPROVED`)

**North Star:** Establish DTD as a trustworthy, useful and financially sustainable dog-trainer discovery and matching service that operates predominantly through automation, with the founder responsible for meaningful decisions rather than routine administration.

- **Strategic coordination:** `docs/DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md` (R0–R13). If not yet installed in this checkout, request synchronisation of the supplied approved roadmap; do not invent its text or stop unrelated authorised work.
- **Delivery execution:** `docs/DTD_ROADMAP_EXECUTION_REGISTER.md`, the relevant domain specifications and open DF/TD findings in `docs/DTD_CURRENT_STATE.md`.
- **Matching:** `docs/DTD_MATCHING_PIPELINE_COMPLETION_ROADMAP.md`, `docs/MATCHING_PIPELINE_REMAINING_COMPLETION_CRITERIA.md` and Decision Contract v2. Preserve M0–M10 identifiers.
- **Operating model:** `docs/specs/OPS_AND_OBSERVABILITY.md`: **OWNER BY EXCEPTION. AUTOMATION BY DEFAULT. AI ANALYSIS WHEN NEEDED.** `/ops` is the sole owner-facing action/evidence surface; read-only AI remains advisory.
- **Authority order:** owner instructions and locked `AGENTS.md`/invariants/decision records govern actions and product policy. The R0–R13 roadmap coordinates stages; it does **not** override an existing locked decision, grant production/billing/provider authority or turn aspirational business metrics into release blockers.
- **Stage discipline:** identify the active R stage, relevant existing DF/M/CF/SR identifiers, inherited evidence and exact exit state. Preserve verified `DONE` items; reopen only for reproducible regression, explicit owner decision or materially unsupported original evidence. Do not require a global re-audit at each transition.
- **Starting release checkpoint:** R0 remediation **cumulative code acceptance is complete** for exact SHA `1ac4138e4d82991501139298cc624be732661119` following the corrected Checkpoint 1 matrix. R1 is accepted with named follow-ups and R2/R3 developer checkpoints are accepted. Resolve changing progress from `docs/DTD_ROADMAP_EXECUTION_REGISTER.md`; corrected R4–R8 runtime acceptance remains **PARTIAL**. Scheduled ingestion remains separately gated by DF-044/045; older recovery targets cannot override the 25 October credential containment. This is a SHA-scoped historical decision, not blanket acceptance of new changes or a claim of production readiness.
- **Beyond launch:** R10 owner/trainer usefulness, R11 separately authorised commerce, R12 observed sustainability and low founder workload; R13 expansion optional. Baselines/targets need measured evidence and appropriate owner decisions. Do not force these outcomes into the R1–R2 remediation gate.

## 1) Preflight Routing (required)

At the start of each new task, do a proportionate preflight. Reuse current-session evidence while it remains fresh; do not repeat the full reading and reporting sequence for every follow-up:

1. Inspect repo root context and user goal.
2. Read the relevant authority files when they have not been read in this session or the task changes their domain:
   - `AGENTS.md`
   - `.codex/skill-policy.toml` (if present)
   - `docs/README.md` for the active documentation map
   - `docs/DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md` (when installed), `docs/DTD_CURRENT_STATE.md`, `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md` and relevant active `docs/specs/` files for the task domain
   - `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` when an old statement resurfaces
   - Historical documentation is preserved outside the checkout and in Git history. Do not load it during routine work; inspect only on an explicit archival-research request.
3. Treat the current session's available skills/plugins/tools as the source of truth.
4. Do not assume a globally installed skill is callable unless it is available in-session. Use available local CLI tools and connected provider integrations; do not claim access not established by actual session or credentials.
5. Give a short progress update when tool work starts. Mention a capability only if its choice, limitation or side effect matters to the work.
6. Route capability selection through `.codex/skill-policy.toml` and use fallback logic if a listed capability is unavailable in-session.

## 2) Skill use

Use a skill when it materially helps the task; read its instructions before use. Announce the first use briefly. Do not create a suggestion table or ask for skill approval when policy already permits automatic use. Keep the active set small.

## 3) Skill Policy Gate

If `.codex/skill-policy.toml` exists, it controls routing behavior.

- Enforce `blocked_skills` always.
- Enforce `allowed_skills` only when present.
- If `require_explicit_composio_invocation = true`, require explicit `$composio-...` user invocation before any Composio skill use.

## 4) Execution authority

The owner's instructions in this session and prior turns are continuing authority for the work they specify. Use the full available local and remote repo capabilities to inspect branches, history, CI, code, issues and authorised provider state. Complete ordinary implementation, tests, documentation, commits and—**after the applicable independent-audit gate**—remote branch sync, approved `main` consolidation and developer-sandbox verification when those steps are within the authorised workflow. Do not request a second yes for the same action. An external system being involved is not, by itself, a new approval gate. **Full access to inspect is not unconditional authority to mutate.**

**Autonomous completion mandate (`LOCKED`):** Do not pause to ask approval from the owner if you know for a fact that an action is the only safe, unambiguous path to finish an authorised or long-standing piece of work (such as deploying an audited commit to the developer sandbox, running end-to-end acceptance checks, consolidating branches, or updating documentation). Proceed directly through execution to completion and report verified results.

Resolve the exact target and effects before consequential actions. Ask once, at the point of action, only for genuinely new authority or an unavoidable provider/platform credential or action-time confirmation. Do not infer a password, OTP or other credential from the owner's project ownership. If an authentication challenge requires the owner, prepare the exact flow, continue independent work, and ask them to complete it in the local trusted UI; never request a secret in chat.

## 4A) Local/remote capability and authentication recovery (`LOCKED`)

1. **Access model.** Use the broadest available *legitimate* capability to work locally and remotely: filesystem and git, GitHub CLI/connector, browser/visual tools, Google Cloud/Firebase CLI/console, database/notification/payment provider consoles or connectors, as appropriate to the task. Never claim those are connected or authenticated until verified. Remote inspection and authenticated reads are normal preflight; mutations require the action-specific gates below.
2. **Prefer existing sessions.** Check non-secret authentication *status and active scope* via a provider's supported CLI, connector or authenticated browser profile. Reuse the owner's existing valid session/token cache through the supported tool; do not copy session cookies, export tokens, impersonate users, bypass MFA/CAPTCHA or place secrets in chat, source, test fixtures or evidence logs. Do not expose token-bearing command output.
3. **Fast reauthentication.** If missing/expired, identify the **single exact provider/account/project, reason, and shortest official login command or trusted UI flow**. Launch it only where safely supported; ask the owner to complete browser/MFA/consent locally, then recheck access and resume the blocked step. Do not terminate a needed interactive login just because it is awaiting owner input; do not loop login attempts. Do not claim an authentication occurred until verified.
4. **Environment scoping.** Before state-changing commands confirm repository, branch/SHA, provider account, GCP project, service, database, credentials tier, likely effects and rollback. Sandbox: `dogtrainersdirectory-dev`, Cloud Run `dtd-api-dev`, Atlas `dtd-sandbox`/`dtd_sandbox`. Production: `gen-lang-client-0028123502`, Cloud Run `dtd-api`, Atlas live `DTD`; production changes are separately gated.
5. **Action classifications.** **READ:** permitted repo/provider discovery under available access. **LOCAL CHANGE:** implement/test/commit on isolated branch when delegated. **REMOTE OR SANDBOX CHANGE:** only after applicable accepted independent audit and within standing authority. **PRODUCTION / LIVE FINANCIAL / CREDENTIAL / AUTH / DESTRUCTIVE REAL DATA / NEW SOURCE RIGHTS:** separate applicable owner authority, documented effects and evidence. This matrix does not override platform permissions or provider confirmation prompts.
6. **No all-stop on login.** Finish independent source review, local tests, docs/evidence prep and all other authorised work while authentication is pending. Mark the one blocked external claim `NEEDS_AUTH`/`NOT_VERIFIED`; keep accepted checkpoints closed. Escalate only the targeted action, never a new general plan approval.
7. **Runtime independence.** Interactive desktop/browser credentials are management/recovery surfaces only. Deployed DTD integrations must use managed least-privilege secrets and service identity as required below; local authenticated logins are not production runtime dependencies.

## 5) Execution Workflow Expectations

1. Prefer non-destructive changes.
2. Implement minimal, high-value changes first.
3. Keep docs and policy files aligned in the same session when governance behavior changes. Stage updated governance and the approved strategic roadmap together when missing, and report if the working repository has not yet received them.
4. Fix stale workspace/path references in authoritative docs when discovered.
5. Use subagents when work benefits from parallel specialist review (for example: frontend UX/copy review, repo audit + validation, accessibility + responsive checks, billing/auth/migration risk review).
6. Use skills/plugins when the task matches a repeatable workflow (for example: frontend audit, copy refinement, accessibility review, test/build verification, release readiness, docs cleanup, evidence audit). Prefer the existing authorised provider session to ad hoc reconfiguration.
7. Apply passive prompt optimization by default before execution:
   - internally rewrite ambiguous or verbose user prompts into concise, constraint-aware execution intent
   - preserve user objective exactly; do not expand scope
   - add explicit output shape and acceptance criteria when missing
   - only skip this rewrite when the user explicitly requests verbatim handling

## 6) Product and release boundaries

Apply the current task authority and the active product contracts. Matching, backend and sandbox work already authorised by the owner may proceed without repeated permission. Public production release, live billing/charging, authentication replacement, credential creation/revocation, destructive real-data changes and material legal/privacy policy changes require applicable owner authority if it has not already been given. Never make unsupported coverage or guaranteed-outcome claims.

## 6A) Independent implementation audit and promotion handoff (`LOCKED`)

For a new code work package delegated to Antigravity or another coding agent, use this sequence. A self-reported completion or access to a remote provider is never evidence of completion.

1. **Scope the work.** Name its R stage, existing DF/M/SR/CF identifiers, locked decisions, touched workflows, exact SHA boundary and verification/cleanup evidence. Codex/ChatGPT may prepare the brief; avoid blocking on which product authors the prompt.
2. **Implement in isolation.** The coding agent can fully inspect local and remote repository/provider state using valid existing authentication. It may implement, test and commit locally on an isolated branch. **Before independent code acceptance, it must not push new implementation commits, merge/open a promotion PR, deploy, mutate provider state or enable gated features.** Read access is not restricted. If a reviewed branch was already pushed historically, preserve Git history and use that exact SHA as evidence rather than pushing again or rewriting history.
3. **Return a compact handoff.** Include base and HEAD SHA, changed files, tests/CI when already available, migrations/provider effects, affected UI/API/data/automation/notification/`/ops` states, known risks and roadmap disposition.
4. **Independent code audit.** A reviewer independent of the implementation author (ChatGPT/Codex as available) reviews the actual cumulative diff and proportionate affected workflow, tests, persistence, fallback, privacy and relevant matrix. Record `DONE`, `PARTIAL`, `OPEN`, `REGRESSED`, `NOT_VERIFIED` or `SUPERSEDED`. The coding agent cannot certify its own changes. A material failure returns **only the proven failing requirement**, not the entire past stage, to implementation.
5. **Post-acceptance execution.** Once the exact SHA has independent code acceptance and scope includes release advancement, **Codex performs** the governed remote push/PR (if still necessary), developer-sandbox deployment, scoped live acceptance, cleanup, and post-checks under standing owner authority. Verify the actual deployed SHA, provider scope, rollback, fixtures, and CI of the resulting `main` state. Never advance a different code SHA under acceptance for the old one.
6. **Freeze and checkpoint continuity.** R0 code acceptance for `1ac4138e4d82991501139298cc624be732661119` and the scoped R1–R3 checkpoints are already granted. Determine the next authorised package from the execution register and current-state evidence; do not repeat completed SR/CF acceptance or R1/R2 consolidation. Remaining corrected R4–R8 runtime/provider evidence stays distinct from source acceptance. Errors in handoff prose are corrected as docs unless they expose a concrete existing-invariant violation. New feature commits require their own proportionate audit, not a reopening of the 2026 remediation.
7. **Production remains separate.** R9/M10 production traffic promotion needs the applicable owner production authority; live Stripe activation/refunds, provider-management credential changes, authentication, new licensed-source use, material policy changes and destructive real-data operations retain separate gates. Sandbox acceptance cannot silently satisfy them.

**Stage evidence contract:** report (i) state transition and exact environment/SHA; (ii) applicable success and negative-case evidence across UI/API/data/fallback/`/ops`, including provider proof where relevant; (iii) cleanup, known limitations and document reconciliation; (iv) one next authorised package. Preserve prior accepted test evidence where still applicable; do not rerun a full suite just to produce a newer timestamp.

## 7) Validation Before Completion

Before finishing a task:

1. Re-read changed files for internal consistency.
2. Run targeted checks relevant to the change scope when practical.
3. Report what was changed, what was validated, and any remaining risks/gaps.
4. If any skill/subagent/plugin/browser/integration was used, include:
   - what was used
   - what each produced
   - how output affected implementation decisions
   - supporting evidence
5. If available capabilities were not used, explain why.
6. Use the evidence template only when it improves clarity for the task.

## Deferred finding record

When an authorised task uncovers a material code, configuration, security, data, or workflow gap that is not fixed in that task, record it before closing the turn. Use `docs/DTD_CURRENT_STATE.md` for verified open findings; use `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` only for actual owner decisions. Each entry needs an ID, observation date, evidence and uncertainty, impact, why it was deferred, and the next action or decision gate. Close an entry only with verification evidence, then remove it from the live open-findings section; git history preserves the audit trail without a growing resolved backlog. This is incremental discovery, not a claim that the codebase has been fully reconciled or audited.

This repository is public. Never put a credential, personal data, private artifact URL, or exploit instructions in the record. Keep the entry actionable but sanitised; report sensitive particulars to the owner separately. Escalate an urgent exposure instead of treating documentation as remediation.

## Credential and provider resilience (locked)

An interactive local browser, desktop login or remembered personal session is a recovery surface only; it must never be a production dependency.

1. Runtime credentials and provider-management credentials live only in the appropriate managed secret store, never in source, local `.env` files, documentation, manifests or literal deployment configuration.
2. The application runtime receives least-privileged credentials. Provider-management identities are separate, narrowly scoped, and may replace or revoke runtime credentials without being used on visitor request paths.
3. Rotate by replacement, not interruption: create a replacement, store a new secret version, validate it on a no-traffic/canary deployment or other safe provider check, promote it, observe it, then revoke the old credential. Never revoke first unless an active incident demands immediate containment.
4. Every material provider dependency needs a sanitised registry record: purpose/scope, runtime versus management identity, last successful verification, next review/expiry, degraded behaviour, independent alert route and recovery owner. Do not record secret values.
5. Before declaring a provider integration or deployment complete, independently verify code, deployed configuration, live-safe provider behaviour and the control-plane ability to recover/rotate it. A successful user-facing request alone is insufficient.
6. If a required provider-management identity or its recovery path is absent, create or update a verified open finding. Do not conceal the gap behind a local browser login or claim autonomous operation.

## 8) Turn Summary Requirement

Include `Active skills this turn:` in responses whenever any skill is active.

## 9) Unacceptable Underimplementation & Strict Verification Mandate (Locked)

Underimplementation and lack of verification are UNACCEPTABLE and SHALL NOT happen again.

When executing any task, migration, or refactoring:
1. **Zero Tolerance for Partial Work:** Do not stop execution simply because the compiler passes or the script runs without errors. You are responsible for the entire end-to-end functionality, including visual state, aesthetics, and edge cases.
2. **Explicit Verification Mandate:** You MUST rigorously verify the final outcome of your changes. For frontend tasks, this means ensuring all styling dependencies (fonts, plugins, external CSS) are active and the UI maintains its premium feel. For backend tasks, this means verifying the entire request lifecycle.
3. **Handle verification limits precisely:** If a required check is unavailable, complete independent work, use another valid verification route where possible, and mark only the unverified claim as such. Request owner action only when that specific missing check cannot be completed without it. Never mark the unverified claim complete.
