# DTD Project Context

**Status:** Primary project context
**Purpose:** Required orientation for work that changes DTD's product, workflows,
runtime, integrations, public claims, or launch behaviour.

## 1. Authority

This document replaces DTD's former project-context layer.
It is the concise, high-signal starting point for implementation. It does not
duplicate detailed rules from the two governing blueprints:

1. `docs/strategy/DTD_MASTER_ARCHITECTURE_AND_MONETIZATION_MATRIX.md`
   defines the target product, public experience, monetization, ranking, and
   fairness model.
2. `docs/strategy/DTD_AUTOMATION_AND_INTEGRATION_SPEC.md` defines the target
   services, data contracts, automation, resilience, communication, and
   operator-evidence model.

The blueprints decide detailed product or engineering questions. This context
decides how agents orient themselves and which detailed source to load next.
It supersedes every older project-context summary, especially material that
describes a waitlist-only, prelaunch-gated, or intro-fee product posture.

`docs/governance/CURRENT_TRUTH_INDEX.md` remains the authority router. Current
runtime evidence describes the migration baseline, not the target state.

## 2. Target Product

DTD is a Greater Melbourne dog-training discovery and matching platform. It
gives owners credible, method-transparent choices and gives trainers rich
digital storefronts, direct owner enquiries, and optional SaaS upgrades.

The launch model is supply-led public discovery:

1. accepted official-website and ABR evidence establishes launch supply, while a separately licensed business-data feed may expand supply after written approval
2. each trainer has a dedicated, SEO-ready business profile
3. owners browse the directory or use guided diagnostic matching
4. trainers claim and enrich their profiles through low-friction verification
5. value precedes paid upgrades; the platform does not charge per lead or take
   a commission on training services

DTD is not a waitlist-first marketing site, a generic listing wall, a lead-fee
broker, or a routine manual-admin business.

## 3. Non-Negotiable Product Rules

1. Public directory discovery and diagnostic matching are target launch
   behaviour across Greater Melbourne.
2. Supply must be real, attributable, deduplicated, quality-gated, and
   suppressible. Never publish fabricated, stale, or delisted trainer data.
3. Owner and trainer flows must be useful without a paid plan. Paid tiers add
   storefront and placement value; they never sell unconfirmed leads.
4. All public pricing is GST-inclusive and flat: free ingested, free claimed,
   Pro, Suburb Featured Sponsor, and Melbourne-Wide Sponsor as defined in the
   product blueprint.
5. Sponsor scarcity is real: suburb inventory is capped, reservation and
   payment state must be concurrency-safe, and sponsor exposure must rotate
   fairly.
6. Matching, ranking, verification, and trust claims must be explainable. AI
   may assist extraction or fit assessment but must fail safely and never make
   unsupported public claims.
7. Every user-facing workflow includes persisted state, downstream automation,
   explicit degraded states, and the required `/ops` evidence.
8. The public website uses Australian English, minimal credible copy, truthful
   claims, one dominant action per page, and the Organic Earthy Luxe visual
   system.

## 4. Actors And Their Value

| Actor | Target outcome |
| --- | --- |
| Dog owner | Find an appropriate local trainer, understand why the result fits, make a protected enquiry, and report an outcome. |
| Trainer / business owner | Discover or claim a useful profile, control business information, receive direct enquiries, and optionally upgrade. |
| Oversight operator | Resolve meaningful exceptions in `/ops` without routine manual administration. |
| Autonomous system | Ingest, deduplicate, verify, rank, manage inventory, deliver messages, follow up, and detect health anomalies. |
| External contributor | Provide lawful source data or signal subject to attribution, quality gates, and suppression controls. |

## 5. Target Operating Spine

`source data -> candidate -> canonical trainer -> published profile -> owner
discovery or match -> enquiry/intro -> trainer response -> outcome/follow-up ->
verified review and ranking signal`

At every transition, retain the product record, audit trail, delivery state,
idempotency protection, fallback behaviour, and relevant `/ops` visibility.
The detailed actor branches and exception cases live in
`docs/governance/WORKFLOW_COMPLETION_SPEC.md` and
`docs/governance/WORKFLOW_SURFACE_MATRIX.md`.

## 6. Target Product Surfaces

| Surface | Intended role |
| --- | --- |
| `/` | Brand entry and quick diagnostic-match intake. |
| `/trainers` | Open All-Melbourne directory with method, specialty, and ranking controls. |
| `/melbourne/:suburb` | Local landing hub with organic results, mobile specialists, and scarcity-aware sponsor placement. |
| `/t/:slug` and `/t/:id` | Rich trainer storefront, trust evidence, booking path, enquiry, and claiming. |
| `/how-it-works`, `/about`, `/trust`, `/pricing` | Explain the platform, standards, and flat commercial model without internal operational language. |
| `/the-first-leash` and `/learn/*` | Open education that helps owners and escalates contextually to relevant local help; it supports rather than displaces directory discovery. |
| `/ops` | Protected, evidence-led exception cockpit. It is not unrestricted admin CRUD. |

Route-level content and state detail belongs in
`docs/COMPLETE_WEBSITE_PAGE_SPEC.md` and the design/state maps, provided it
conforms to the two blueprints.

## 7. Capability Map

| Capability | Target change | Detailed authority |
| --- | --- | --- |
| Supply seeding | Preserve the accepted initial batch and build the separately gated licensed-feed acquisition path, Gemini-assisted structuring, canonical merging, quality gates, idempotent seeds, and delisting suppression. | `docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`; product blueprint 2.1; automation blueprint 2.5, 6, 8. |
| Directory and SEO | Deliver browseable trainer and suburb surfaces, slugs, canonical metadata, structured data, and graceful zero-result radius expansion. | Product blueprint 2, 8, 10; page spec. |
| Matching and enquiries | Deliver guided fit assessment, explainable results, protected contact, reply routing, engagement, outcome, and follow-up. | Product blueprint 2, 8, 11; workflow and communication contracts. |
| Claiming and trainer tools | Add ABN checks, SMS/email passwordless claiming, dispute states, profile editing, booking and lead access. | Product blueprint 3; automation blueprint 6, 8. |
| Revenue and inventory | Replace legacy conversion-fee behaviour with flat Stripe subscriptions, inventory reservation, webhook idempotency, refunds, and customer self-service. | Product blueprint 5, 7, 12; automation blueprint 2, 5, 8. |
| Ranking and fairness | Rank by relevant quality and outcome signals, enforce sponsor caps and fair rotation, preserve an earned organic position. | Product blueprint 8 and 9. |
| Education | Consolidate education into the native open React learning hub, preserve local progress, and add relevant escalation bridges. | Product blueprint 4; education architecture specification. |
| Operations | Materialise delivery, claim, ingestion, billing, health, and exception evidence in `/ops` with bounded one-click triage. | Product blueprint 14; automation blueprint 9; operations specifications. |
| Reliability | Use a transactional outbox, isolated jobs, health/degradation signals, backups, recovery procedures, and alerting. | Automation blueprint 3, 5, 11. |
| Google migration | Move runtime capability to Cloud Run, Scheduler/Tasks, Firebase Hosting/Auth/Storage, Gemini, and monitoring without a database rewrite. | `docs/strategy/DTD_GOOGLE_ECOSYSTEM_MIGRATION_AND_TASK_SPEC.md`; detailed blueprints. |

## 8. Intended Architecture

1. Keep FastAPI and MongoDB Atlas while modernising runtime infrastructure.
   A database rewrite to Firestore or SQL is not part of this migration.
2. Retain specialist systems that already fit the product: Stripe Australia for
   subscriptions, ABR for statutory ABN verification, and Resend for
   transactional mail.
3. Use Google services where they improve reliability or delivery: Cloud Run,
   Cloud Scheduler, Cloud Tasks, Firebase Hosting, Firebase Authentication and
   Storage, Gemini, permitted Maps experiences, and Cloud Monitoring. Google
   Places and Gemini Search Grounding are not persistent trainer-acquisition
   sources; follow `docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`.
4. Use a transactional outbox and idempotent handlers for external effects.
   Never lose, silently repeat, or falsely report an enquiry, OTP, webhook, or
   lifecycle message.
5. Treat backups, restore testing, deep health checks, degraded states, and
   alerts as product requirements, not post-launch polish.

## 9. Migration Baseline And Required Replacement Work

The current codebase is a migration baseline. Existing behaviour is not proof
that it belongs in the target product. Unless explicitly retained by a
blueprint, replace the following legacy posture:

1. public-matching gates and owner waitlist-first public experience
2. dynamic pricing, fixed-intro-fee, conversion-fee, and legacy billing-retry
   loops
3. prelaunch claim-state gates and fragmented trainer lifecycle paths
4. isolated worker assumptions that can silently fail without durable queues,
   health evidence, or recovery
5. placeholder/test-only directory supply, raw internal scoring language, and
   weak trainer profile surfaces
6. duplicate education proof-of-concepts and disconnected learning routes

Preserve compatibility deliberately: use redirects, explicit state migration,
idempotent upserts, provider-event deduplication, and rollout rollback paths.
Do not silently remove data, public routes, valid claim links, or active
integrations.

## 10. Delivery Rules

Programme delivery and Codex-Antigravity coordination are governed by
`docs/process/DTD_DELIVERY_ORCHESTRATION.md`. That protocol controls task
handoff and verification only; it does not replace this context or either
blueprint.

1. Build vertical workflows, not isolated pages or endpoints. Each task must
   cover actors, records, automation, failures, notifications, and `/ops`.
2. Parallelise independent implementation: public UI, data/claim services,
   runtime preparation, and tests may proceed together. Do not concurrently
   edit the same workflow or source files.
3. Verify locally before staging. Use targeted tests, production builds,
   browser checks at desktop and mobile sizes, and lifecycle/ops proof for
   workflow changes.
4. Treat external provider configuration, live data ingestion, live billing,
   DNS changes, and production deployment as explicit rollout actions. Their
   code can be prepared and verified without activating them.
5. No feature is complete on a visual `200` alone. Completion requires the
   exact end-to-end evidence defined by the workflow contract and launch gate.

## 11. Progressive Reading Guide

Read only the source needed for the work at hand after this context:

| Work | Read next |
| --- | --- |
| Product, pricing, ranking, supply, education | Product blueprint. |
| Automation, integrations, state, reliability | Automation blueprint. |
| Public routes, copy, CTA hierarchy, visual structure | Complete Website Page Spec and Website Wireframe Spec. |
| User or operator workflow | Workflow Completion Spec, Workflow Surface Matrix, Stakeholder Communication Contract, and Operations Console Spec. |
| `/ops` design or responsibilities | Operations specifications and Ops Cockpit Responsibility Model. |
| Build, launch, release evidence | Build Checklist, Launch Gate, Integrity Audit, and Execution Status. |
| Google infrastructure migration | `docs/strategy/DTD_GOOGLE_ECOSYSTEM_MIGRATION_AND_TASK_SPEC.md` plus the relevant provider documentation. |

## 12. Context Maintenance Rule

Keep this file concise. Add only a project-wide decision that changes how an
agent should orient itself. Put detailed rules in the owning blueprint or
domain specification, update `CURRENT_TRUTH_INDEX.md` when authority changes,
and remove superseded context rather than creating another summary.
