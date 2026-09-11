# DTD Delivery Orchestration

Status: active programme-delivery protocol

## Purpose

This file coordinates delivery between the owner, Codex, and Antigravity. It
does not define the DTD product, replace either blueprint, or create a parallel
backlog. Product and technical decisions remain with the authorities listed in
`docs/governance/CURRENT_TRUTH_INDEX.md`.

## Delivery Objective

Deliver the target DTD platform quickly without losing workflow completeness,
runtime reliability, or evidence. Work may proceed in parallel when ownership
and dependencies are explicit; it must not be serialised merely for ceremony.

## Authority And Boundaries

Read in this order:

1. `AGENTS.md`, `.codex/skill-policy.toml`, and `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
2. `docs/governance/CURRENT_TRUTH_INDEX.md`
3. `docs/standards/DTD_PROJECT_CONTEXT.md`
4. `docs/strategy/DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md`
5. `docs/strategy/DTD_AUTOMATION_AND_INTEGRATION_SPEC.md`
6. `docs/strategy/DTD_GOOGLE_ECOSYSTEM_MIGRATION_AND_TASK_SPEC.md` for migration work
7. `docs/process/FEATURE_WORKFLOW_IMPLEMENTATION_CONTRACT.md` for any user, automation, or `/ops` workflow

The current codebase and historical execution records are a migration baseline.
They do not limit target-state work unless an authority explicitly retains a
behaviour for compatibility or rollout safety.

## Roles

| Role | Accountable for | Must not do alone |
| --- | --- | --- |
| Owner | priorities, commercial and launch decisions, credentials, external-account approval | silently accept a product or provider cutover |
| Codex | task packets, integration, conflict resolution, evidence, end-to-end validation | expose secrets, make unapproved external changes, overwrite another worker's work |
| Antigravity | bounded implementation from an accepted task packet, local validation, precise handoff | redefine authority, change provider configuration, deploy, or edit unowned files |

## Work States

`planned -> ready -> building -> handoff -> integration -> verified-local -> ready-for-external-action -> released -> observed`

1. A task is `ready` only when its authority references, file ownership,
   dependencies, migration behaviour, and completion evidence are stated.
2. Independent ready tasks may start immediately.
3. `ready-for-external-action` means code and local evidence are complete but
   needs an owner-approved provider, credential, deployment, or live-data step.
4. A failed check returns the task to `building`; an incompatible handoff is
   resolved before integration rather than patched around.
5. `observed` requires the relevant runtime and `/ops` evidence, not only a
   successful deployment.

## Delivery Waves

These are dependency guides, not unnecessary stage gates.

| Wave | Scope | Dependency rule |
| --- | --- | --- |
| P1 | Remove legacy product gates, intro-fee loops, and old public-posture assumptions. | First for behaviour being replaced; isolated preparation may run in parallel. |
| P2 | Canonical trainer data, lawful ingestion, ABN verification, claims, and profile ownership. | Depends on P1 only where legacy states are removed; data-model preparation can start earlier. |
| P3 | Directory, storefronts, owner discovery/enquiries, and `/ops` evidence. | Full claim and profile controls depend on P2; independent visual shells may proceed in parallel. |
| P4 | Flat subscriptions, sponsor inventory, payments, quality seeding, and reliability completion. | Depends on P1 billing removal and P2 identity/data rules. |
| M1-M4 | Google runtime preparation, Gemini, Firebase Auth, Hosting, Cloud Run, Scheduler, Tasks, Monitoring, and recovery. | Non-invasive preparation may run beside P1-P3. No production cutover before the affected product path is locally verified. |

## Task Packet

Every implementation task handed to Antigravity or another worker contains:

1. task ID, wave, and objective
2. exact authority sections and acceptance criteria
3. owned files and explicitly excluded files
4. dependencies and permitted parallel work
5. migration baseline to preserve, replace, or bridge
6. expected routes, records, services, automations, and `/ops` evidence
7. local validation commands and required browser checks
8. external actions, if any, marked separately as owner-approved follow-up

No task packet includes secrets, access tokens, private customer data, or an
instruction to make an unapproved provider change.

## Completion Standard

For a feature affecting users, automation, billing, data, or operations, the
completion evidence must cover all applicable items:

1. initiating route or interaction, including mobile where public
2. persisted state, migrations, idempotency, and compatibility behaviour
3. downstream jobs, notifications, and external-effect deduplication
4. invalid, duplicate, expired, suppressed, failed, and degraded branches
5. exact `/ops` evidence for exceptions, delivery state, retries, and review
6. targeted tests, build, and affected browser paths
7. rollback or compensation for irreversible or externally visible effects

Use `docs/process/FEATURE_WORKFLOW_IMPLEMENTATION_CONTRACT.md` to trace these
branches. A rendered route, successful request, or passing unit test alone is
not completion.

## Failure, Recovery, And Compensation

1. Use idempotency keys and transactional outbox records for external effects.
2. Make retries bounded, observable, and safe to repeat.
3. Materialise meaningful delivery failure, suppression, claim dispute,
   reservation expiry, refund, delist, and health-degradation states in `/ops`.
4. Prefer explicit rollback or compensating actions over silent deletion:
   release inventory, disable a pending seed, preserve a legacy route with a
   bridge, refund an incorrect charge, or mark a delivery as failed for review.
5. Do not retry a provider failure indefinitely or conceal it behind a green UI.

## Handoff And Integration

An Antigravity handoff must state:

1. task ID and authority references used
2. files changed and files intentionally untouched
3. behaviour completed, including migration/compatibility treatment
4. validation run and results
5. unresolved risks, missing credentials, or external actions
6. any conflict with another active task

Codex integrates only reviewed handoffs, runs cross-task validation, updates
current execution state, and reports the evidence. Preserve the existing dirty
worktree: never discard or reformat unrelated user or Antigravity changes.
