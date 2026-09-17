# Execution Status

## Purpose

This file is the sole current-state controller for DTD execution.

It owns:
1. current objective
2. current blocker
3. current priority order
4. current accepted scope
5. explicitly deferred items
6. current verification status
7. current risks
8. restart protocol
9. concise append-only execution log

It does not define:
1. product truth
2. workflow completion rules
3. page-level behavior
4. `/ops` product behavior
5. standards or launch gates

## Superseding implementation status — 18 September 2026

The owner has approved the education separation and Stripe-live Pro-trial
anchor. This status supersedes older execution-log statements that prohibited
education-workspace changes or left either decision unresolved.

- The First Leash is owned and deployed from `DTD-education-extended`; main DTD
  retains only branded links and redirects for `/education/*` and
  `/the-first-leash/*`.
- Duplicated education pages, APIs, content, POCs, generated course assets and
  education-only brand files have been deleted from main DTD, not archived.
- The cross-site return link is static and query-free, so behavioural intake
  details never cross the application boundary in a URL.
- Pro-trial eligibility is gated by a live Stripe key plus
  `STRIPE_LIVE_ANCHOR_AT`. Stripe creates the 30-day trial; webhooks persist the
  provider dates and consume eligibility; a daily idempotent job sends the
  day-23 warning and records its result in notification and system state.
- Stripe remains in test mode. The trial cohort therefore remains safely
  inactive until the live key and anchor timestamp are set together.
- The canonical per-business suburb-sponsorship cap is 4.

## Current Objective

Launch the DTD main website with its accepted attributable trainer supply and
working trainer-submission path. After launch, complete the separately gated
licensed-feed acquisition integration defined in
`docs/strategy/DTD_ACQUISITION_AND_INGESTION_PIPELINE.md`.

## Current Blocker

MongoDB Atlas cluster `DTD` was resumed by the owner and fully synchronised with all 45 trainer profiles and system collections; Cloud Run `dtd-api` is healthy (`/api/health` returns `200` with `database: available`).
The single remaining launch blocker is the Vercel DNS cutover for `dogtrainersdirectory.com.au`:
- Point A record `@` to `199.36.158.100`
- Point CNAME `www` to `gen-lang-client-0028123502.web.app.`
- Add TXT `@` to `hosting-site=gen-lang-client-0028123502`
- Add ACME challenge TXT records (`exCJ2FwW2cwKT8ZYFrAzLwiKGyjOeWb1KluIzq7vGLY` and `vjwCoVei22N1VKFtNU80A0Oqkxz0SbkSzx7iB_KgveI`)
- Preserve all existing Zoho MX and SPF TXT records.
The post-launch acquisition blocker is separate: Sensis/Thryv has not yet confirmed a suitable SAPI/successor feed or supplied written data-use rights, pricing, schema, credentials, or a contract. No adapter can be truthfully built against an unknown interface.

## Current Priority Order

1. R1/M4/M3-Main: fix Cloud Run startup, deploy the API and DTD-only Firebase Hosting site, attach the main domain, and verify the acquired listing plus trainer-submission journey. Do not touch `dtd-first-leash` or the education workspace.
2. M2-Claim: add and verify Firebase Phone Auth for Australian numbers while preserving token validation, expiry/invalid states, email fallback, and `/ops` delivery evidence.
3. P4-D expansion: evaluate the Sensis/Thryv response, record written rights, then implement and dry-run the exact licensed adapter. MacroMatch/TotalCheck are not assumed to be discovery products.
4. Post-launch activation: enable authenticated scheduled acquisition and maintenance only after source contract, adapter, dry-run, suppression, quality, and `/ops` evidence pass with explicit owner authority.
5. E1 expansion: grow beyond the accepted initial batch toward 100+ authentic Greater Melbourne profiles using only approved sources; website launch does not wait for this expansion.

## Active Target Launch Plan

This is the current delivery plan. It sequences only file or runtime dependencies;
it is not a substitute for the canonical implementation pack or a reason to hold
independent local work. Every implementation packet uses the workflow contract.

| ID | Work package | Delivery owner | May run with | Must wait for | Completion evidence |
| --- | --- | --- | --- | --- | --- |
| P1-R | Replace legacy public posture and intro-fee remnants with the target directory and matching posture. Own `backend/server.py`, `backend/.env.example`, affected frontend policy/pages, and directly related tests. | Antigravity, Codex review | M1-AI and P4-D preparation | No other task edits these files. | No active legacy fee/waitlist public behaviour or configuration; target routes remain coherent; targeted backend/frontend tests and browser checks pass. |
| P2-A | Accept or remediate canonical trainer schema, ABN verification, claim, session, duplicate, expiry, dispute, notification, and `/ops` branches. | Codex validation, Antigravity only for bounded fixes | M1-AI | P1-R where the same route/config is changed. | API, records, delivery state, fallback branches, and `/ops` cases are evidenced end to end. |
| P3-A | Accept or remediate open directory, suburb pages, storefront, guided matching, protected enquiry, outcome, and Ops surfaces. | Codex validation, Antigravity only for bounded fixes | M1-AI and P4-D preparation | P1-R public-posture ownership is released. | Desktop and mobile browser checks, accessibility/console checks, product records, notifications, and `/ops` evidence pass. |
| P4-C | Build sponsor inventory: caps, atomic reservation, expiry/release, Stripe lifecycle linkage, fair rotation, refund/cancel handling, and operator evidence. | Antigravity, Codex review | M1-AI and P4-D preparation | P1-R; no concurrent edits to billing or `backend/server.py`. | Concurrent reservation test, webhook/idempotency test, recovery paths, ranking/placement proof, and `/ops` exception evidence pass. |
| M1-AI | Add a fail-safe Gemini client for structured source extraction and diagnostic fit scoring, retaining deterministic fallback and provenance. | Antigravity, Codex review | P1-R, P2-A, P4-D preparation | No live key required for local mock tests. | Schema-invalid, timeout, rate-limit, and fallback tests pass; no unsupported claim is published; `/ops` exposes material degradation. |
| P4-D | Preserve the accepted official-website/ABR launch batch and add a licensed Sensis/Thryv SAPI/successor adapter only if written rights and a concrete interface are supplied. | Antigravity, Codex review | M1-AI | Supplier response, approved contract/use record, schema, credential, and explicit production activation. | Dry-run produces traceable candidates; duplicate/suppressed/invalid/revoked-contract branches are safe; no publication from AI confidence alone; `/ops` exposes source health and review work. |
| M4-Runtime | Correct Cloud Run local runtime preparation: port `8080`, deep health endpoint, container test, cron endpoint authentication, outbox/Task adapter, and health degradation evidence. | Antigravity, Codex review | M1-AI and P4-D preparation | P1-R or P4-C if they own `backend/server.py`. | Local container health probe, authenticated cron tests, idempotent task handling, and `/ops` degradation cases pass. |
| M2-Claim | Replace or bridge the current claim OTP client with Firebase Phone Auth while preserving existing claim records, fallback, and dispute behaviour. | Antigravity, Codex review | M3-Main preparation | P2-A; Firebase project and test-number setup for live verification. | Australian-number validation, token verification exchange, invalid/expired states, fallback, and `/ops` delivery evidence pass. |
| M3-Main | Configure Firebase Hosting for the main React directory only, including SPA rewrites and deployment verification. | Antigravity, Codex review | M2-Claim | P3-A build stability; Firebase project configuration. | Production build and Hosting preview pass; direct-route refresh works; main-site browser checks pass. |
| M3-Learn | Define the hosting interface for `learn.dogtrainersdirectory.com.au` without editing or interacting with the separate education workspace. | Codex with education owner | None | Education owner supplies its deployable artifact and approval. | A separate, approved hosting handoff exists; no DTD-directory task writes to the education workspace. |
| E1 | Expand the accepted initial supply toward 100+ authentic Greater Melbourne profiles from the approved licensed feed and approved first-party sources. | Owner authorises; Antigravity executes; Codex validates | None | Licensed P4-D adapter, required provider access, written source rights, and data-quality evidence. | 100+ attributable records, dedupe and suppression proof, ABN/quality state, `/ops` review data, and no fabricated listing. |
| R1 | Launch the main DTD site first using accepted supply and the trainer-submission path; then complete remaining provider cutovers and production observation. | Owner approved; Codex coordinates; Antigravity executes bounded commands | None | Healthy Cloud Run/Firebase paths and public-domain evidence; E1 expansion is not a launch prerequisite. | Live acquired profile, accepted submission path, deep-health checks, domain/TLS proof, and explicit limitations for any provider path not yet verified. |

### Parallel Lanes

1. Keep one owner on the launch-critical Cloud Run, Firebase Hosting, custom-domain, listing, submission, and `/ops` journey until it is verified.
2. The Sensis/Thryv supplier-response lane may proceed independently as read-only commercial evaluation; it must not create an adapter or approve use before concrete written terms and a schema exist.
3. Do not run a Places harvest, generic search scraper, expansion seed, or acquisition scheduler in parallel with launch.
4. M2 Firebase Phone Auth may follow the initial public launch without redefining the existing email/token fallback.

### Launch Definition

The initial public website launch requires a healthy deployed API, the DTD-only
Firebase Hosting target, valid domain/TLS, accepted attributable supply, one
working acquired profile, trainer submission with publish/hold safety, protected
`/ops` evidence, and desktop/mobile route checks. Any unverified Stripe,
Firebase Phone Auth, scheduled acquisition, monitoring, or backup path must be
declared as a post-launch limitation rather than fabricated as complete.
Education remains a separate workspace and is not part of this launch.

## Current Accepted Scope

In scope: the owner-authorised DTD main-site deployment and the work necessary
to make its accepted listing and trainer-submission workflow live, plus the
documentation-only acquisition reconciliation in execution-log item 28.

Out of scope without explicit approval: database rewrites, licensed-feed
activation, expansion harvesting/seeding, destructive data changes, education
workspace changes, and unrelated refactors.

## Explicitly Deferred Items

Only defer a target requirement when its task packet records an external
dependency, owner decision, or deliberate rollout boundary. A legacy product
gate is not a deferral reason.

## Current Verification Status

Historical proof below describes the former launch posture and must not be used
as proof of target-state completion. Each wave establishes new local, runtime,
and `/ops` evidence under its task packet before it can be released.

## Current Runtime And Infrastructure Truth

Treat existing infrastructure and runtime behaviour as baseline inventory.
Retain only the specific compatibility, data-safety, and rollout protections
identified by the authoritative blueprints and task packets.

## Current Risks

1. existing implementation, documentation, and tests retain contradictory prelaunch assumptions
2. the dirty worktree contains concurrent user and Antigravity changes
3. external service cutovers require separate evidence and owner-approved action
4. tasks that share data models or public routes can conflict without explicit ownership

## Restart Protocol

Any future session should restart from:
1. `AGENTS.md`
2. `.codex/skill-policy.toml`
3. `docs/process/CODEX_EXECUTION_PLAYBOOK.md`
4. `docs/governance/CURRENT_TRUTH_INDEX.md`
5. `docs/standards/DTD_PROJECT_CONTEXT.md`
6. `docs/process/DTD_DELIVERY_ORCHESTRATION.md`
7. this file
8. the current repository state

Session-start rules:
1. inspect current worktree state first
2. distinguish baseline behaviour from target requirements
3. assign file ownership before parallel work begins
4. preserve valid compatibility and data-safety behaviour deliberately
5. never use historical proof as target-state release evidence

Launch authority:
1. final Go/No-Go authority remains the owner
2. launch approval must be explicit and evidence-backed

## Append-Only Execution Log

1. `2026-06-03`
- repo-anchored handoff established as safer than chat-memory continuation
- trust-first next-work order locked for post-Ops-foundation execution

2. `2026-06-06`
- documentation cleanup decomposed into locked chunks:
  - final file set
  - ownership rules
  - keep / merge / delete decisions
  - exact content allocation

3. `2026-06-07`
- code-informed refinement added to documentation cleanup
- `/ops` and `OPERATIONS_CONSOLE_SPEC.md` confirmed as preservation-sensitive
- bounded Layer 1 review-state writes confirmed as implemented truth
- documentation system cleanup completed:
  - workflow completion authority created
  - single execution-status authority created
  - parallel roadmap/handoff control docs retired
- startup seed control tightened in code:
  - seeds require explicit `ENABLE_STARTUP_SEEDS`
  - worker startup no longer participates in seeding
- optional local compose stack aligned toward DTD naming and worker topology

4. `2026-06-08`
- Phase 1 trust restoration completed
- local validation passed:
  - `python3 -m compileall backend`
  - `cd backend && ../.venv/bin/pytest -q tests/test_public_mode_unit.py tests/test_runtime_control_unit.py tests/test_lifecycle_endpoints_unit.py`
  - `cd frontend && CI=true npm test -- --watch=false --runInBand src/pages/Ops.test.jsx`
  - `cd frontend && npm run build`
- trusted state synced to `origin/main` at commit `12b049b8fb6ef06728a4dd6bd3f966f5e475ea4b`
- Vercel production deployment for commit `12b049b8fb6ef06728a4dd6bd3f966f5e475ea4b` reached `READY`
- live backend `/api/config` and `/api/oversight` now match the locked supply-first posture and current `/ops` contract
- current safe hosted verification routes returned `200`:
  - `/`
  - `/trainers`
  - `/ops`
- next active phase is launch-readiness proof, not further trust restoration

5. `2026-06-08`
- Phase 2 started
- `node scripts/check_prelaunch_release_gate.js` returned `PRELAUNCH_RELEASE_GATE=PASS`
- runtime-evidence review narrowed the active launch blockers to:
  - live trainer submission E2E proof
  - live Stripe/Resend provider exercise
  - campaign-attribution and discovery-pickup proof
  - long-window autonomous-loop proof
- stale closed-blocker rows in `RUNTIME_EVIDENCE_ALIGNMENT_MATRIX.md` were corrected so the matrix matches the current `/ops` contract and hosted runtime evidence

6. `2026-06-08`
- Phase 2 launch-readiness audit tightened the next human gate
- code audit confirmed the first live trainer-submission proof is provider-coupled, not inert:
  - `create_submission()` can trigger `notify_submitter_result()`
  - `create_intro()` can trigger `bill_intro()` and `notify_trainer_new_intro()`
- next live proof therefore requires deliberate owner approval before exercising real provider paths

7. `2026-06-08`
- owner decision recorded: defer provider-coupled live proof
- live trainer submission, notification, and billing-coupled exercise are no longer current Phase 2 blockers
- those proofs are reserved for the final actual-domain activation decision instead of the current safe hosted path

8. `2026-06-08`
- Phase 2 wording tightened to reflect the actual proof target
- nearest-to-live hosted verification already exists for the synced frontend alias, live backend contract, and `/ops` surface
- remaining current blockers are now described as hosted-path attribution/discovery proof and elapsed-window loop proof, not generic final-live proof

9. `2026-06-08`
- nearest-to-live hosted oversight snapshot re-checked against the current backend target
- hosted evidence now confirms:
  - discovery summary is present with promoted rows
  - loop statuses expose interval and age signals on the trusted hosted path

10. `2026-06-09`
- remaining DTD work reprioritised around how the owner actually uses `/ops`
- the new active order is:
  - decision surfaces first
  - supply/readiness decision support second
  - lifecycle/support wording cleanup third
  - monitoring/system-health separation fourth
  - final verification group later
- final public launch approval remains withheld until the later verification group is complete
- remaining non-provider blocker language narrowed to:
  - campaign-attribution persistence and clean discovery-lineage proof
  - elapsed-window autonomous-loop proof

11. `2026-06-08`
- hosted Phase 2 non-provider proof completed on the trusted hosted path
- browser-driven landing and waitlist proof established a retained attribution cohort:
  - `campaign=phase2-proof`
  - `source=lp`
  - `entry_events_30d=3`
  - `waitlist_joins_30d=1`
- hosted duplicate-path discovery proof established current discovery intake and processing without creating a new public trainer row:
  - `POST /api/discovery` accepted a pending candidate for `https://www.dogforce1.com.au`
  - hosted oversight moved from `pending=1, duplicate=0` to `pending=0, duplicate=1`
  - hosted discovery heartbeat then recorded `duplicates=1`, `handled=1`, `last_run=2026-06-07T18:44:10.935161+00:00`
- elapsed-window hosted loop proof established that short-cadence loops continued refreshing over time:
  - `ranking`, `pricing`, and `health` stayed within expected cadence across repeated samples
  - `discovery` advanced from `last_run=2026-06-07T18:34:09.921276+00:00` to `last_run=2026-06-07T18:44:10.935161+00:00`
- current active Phase 2 blockers are therefore closed
- Phase 2 is complete under the current governance scope
- next active phase is owner review and launch decision preparation
- only deferred actual-domain activation proofs remain

12. `2026-06-08`
- Phase 3 owner review and bounded Go/No-Go completed
- Browser review verified the key trusted hosted surfaces used for owner review:
  - `/`
  - `/trainers`
  - `/ops`
- launch-gate assessment confirmed the hosted-path non-provider evidence set is sufficient to move forward
- bounded decision recorded:
  - Go to the deferred actual-domain activation slice after remaining `/ops` completion work
  - No-Go on final public launch approval until the provider-coupled actual-domain checks pass

13. `2026-06-09`
- remaining `/ops` optimisation work completed
- local oversight contract extended with:
  - `ops_supply_geography`
  - `ops_supply_trends`
- overview now leads with decision-summary reading and plain-language next-step guidance
- work queue now exposes explicit decision guidance in both the table and the detail panel
- trainer supply now exposes geography coverage, demand gaps, pace, blocked supply, and intro-ready trajectory signals
- monitoring/system health remains visible as a supporting section instead of the primary operator reading surface
- local browser verification confirmed the decision-first `/ops` flow on desktop and mobile against the updated local backend contract

14. `2026-09-09`
- target launch plan recorded in this current-state controller rather than a new roadmap document
- immediate Antigravity work is `P1-R`; `M1-AI` may run in parallel because it has separate primary files
- live harvesting, provider configuration, deployment, and launch remain rollout actions after their local artefacts and evidence are ready
- `M3-Learn` remains an education-owner handoff only; DTD-directory delivery must not interact with the separate education workspace

15. `2026-09-09`
- `P1-R` accepted for progression after independent targeted backend validation (`86 passed`) and scoped diff integrity checks
- public config reads no longer write launch-phase state; active trainer billing and Ops exceptions now use subscription lifecycle data while historical intro records remain archival
- browser acceptance remains part of `P3-A`; it is not claimed by the local test/build evidence
- next implementation packet: `M1-AI`

16. `2026-09-09`
- `M1-AI` implemented and verified locally with fail-safe Google Gemini foundation
- added structured trainer-source extraction with strict schema validation (`training_philosophy`, `specialties`, `service_formats`, `serviced_suburbs`, `confidence`, `reasoning`, `signals`)
- added explainable diagnostic matching with hard tier-neutrality (commercial tier stripped from candidate data sent to model)
- added deterministic heuristic fallbacks across extraction, matching, and evidence scoring (no API key required for local development)
- enforced safety boundary: AI output alone never publishes a profile, verifies an ABN, or creates unsupported public trust claims
- bounded degradation events persisted and exposed in `/ops` exception work queue and investigation views without leaking prompts, source text, or secrets
- 19 focused tests in `backend/tests/test_ai_scoring.py` pass cleanly; 189 total backend unit tests pass

17. `2026-09-09`
- `M1-AI` safety correction independently accepted: an AI-derived confidence score alone cannot publish a profile, mark it verified, assert ABN verification, make it contact-ready, or reactivate it for public matching
- publication now requires separately obtained statutory ABN evidence and the existing quality threshold; held trainer submissions remain explicit high-severity `/ops` review cases with model provenance
- independent validation passed: `54` focused M1/P2/claim tests, `170` unit tests, Python compilation, and the scoped diff-integrity check
- next active packet: `P2-A` claims and data-workflow acceptance, with bounded remediation only where evidence identifies a target-state gap

18. `2026-09-09`
- `P2-A` claims and canonical trainer-data workflow accepted after bounded remediation and comprehensive deterministic validation
- bounded fixes applied to `backend/server.py`: added 60-second challenge resend cooldown (`TRAINER_CLAIM_RESEND_COOLDOWN_S`), replay rejection (409) with dispute/audit log, notification delivery failure state rollback to `unclaimed`, duplicate identity matching on submissions to enrich unclaimed records or hold competing claimed submissions as disputed cases, and explicit `/ops` exception visibility with reason tokens
- independent validation passed: `36` focused claim/ABN unit tests, `200` total backend unit tests, Python compilation, and clean scoped diff integrity
- next active packet: `P3-A` (open directory, suburb pages, storefront, guided matching, protected enquiry, outcome, and Ops surfaces) or `P4-C` sponsor inventory reservation/lifecycle

19. `2026-09-09`
- `P2-A` claim dispute state-lock correction verified and accepted: competing direct claim against `claimed` or `claim_disputed` profile now atomically locks `trainer.claim_status` to `claim_disputed` while preserving existing ownership history, claimed timestamp, and tier data
- normal claim initiation and verification are locked out on disputed profiles (returning HTTP 409 without issuing codes, sessions, or ownership mutations); `/ops` explicitly surfaces both the high-severity dispute event and the profile's disputed ownership state in detail rows and risk reason codes
- independent validation passed: `39` focused claim/ABN unit tests (including regressions for repeated attempts on already disputed profiles and verification lockout), `203` total backend unit tests, Python compilation, and clean scoped diff integrity

20. `2026-09-09`
- `P2-A` unverified claim-start security correction verified and accepted: `POST /trainers/{trainer_id}/claim` against an already `claimed` or `claim_disputed` profile now rejects with HTTP 409 without mutating profile records, issuing codes/sessions, revoking ownership, or creating unverified dispute locks in `/ops`
- stale verification attempts after another claim completes are denied (HTTP 409) with challenges marked stale rather than altering the claimed profile or flooding `/ops` with high-severity dispute cases
- independent validation passed: `42` focused claim/ABN unit tests (including regressions for arbitrary claimant denial, profile preservation, stale verification rejection, and zero unverified `/ops` dispute cases), `206` total backend unit tests, Python compilation, and clean scoped diff integrity

21. `2026-09-09`
- `P3-A` accepted locally: public directory and suburb storefronts, trainer trust/profile presentation, guided matching, consent-gated enquiry/contact release, engagement tracking, notification fallback state, and `/ops` visibility now form one bounded end-to-end workflow
- public trainer responses use an explicit storefront allowlist; protected email and phone fields remain hidden until a consented introduction, while eligible Pro website and booking links remain public
- `/ops` authentication now fails closed to the passcode form for fresh or rejected sessions, and message targets are masked in oversight output
- independent validation passed: `211` backend unit/AI tests, Python compilation, `12` targeted frontend tests, production frontend build, desktop browser journeys, and a 390px route matrix with no console/page/request failures or horizontal overflow
- no live provider calls, production deployment, harvesting, or education-workspace interaction occurred; rollout actions remain separately gated

22. `2026-09-10`
- `P4-C` accepted locally: claimed trainers can select fixed GST-inclusive Pro, suburb sponsor, or Melbourne-wide subscription plans, enter hosted Stripe Checkout, and return to the authenticated billing lifecycle; customer self-service portal return paths preserve the same scoped trainer context
- sponsor inventory now enforces two positions per suburb, five citywide positions, one business per suburb, and a five-suburb trainer cap through atomic reservations; holds expire and release idempotently through a dedicated 15-minute maintenance loop
- Stripe subscription, invoice, cancellation, refund, and replay paths update entitlement through webhook metadata and subscription identity; active sponsor entitlement is withheld when its reservation cannot be activated, while failures remain visible for review
- directory placement fairly rotates paid sponsor positions and preserves an unbuyable organic `Community Choice`; `/ops` exposes active/reserved positions and inventory exceptions, while refund execution remains disabled by default behind explicit technical-owner configuration, reason capture, Stripe idempotency, downgrade, release, and audit handling
- independent validation passed: `231` backend unit/AI tests, Python compilation, all `35` frontend tests, production frontend build, diff-integrity checks, and desktop plus 390px rendered checks for billing, sponsor inventory, and paid-versus-earned directory labels with no horizontal overflow
- no live Stripe calls, provider configuration, production deployment, trainer harvesting, seeding, or education-workspace interaction occurred; the next active packet is `P4-D` preparation only

23. `2026-09-10`
- `P4-C` credential-containment correction accepted: Checkout and Customer Portal return URLs now contain only the non-secret trainer identifier; trainer claim/action bearer tokens remain in same-origin browser session storage and are never sent to Stripe or embedded in provider-facing URLs
- independent validation passed: `23` P4 inventory/subscription tests, `232` backend unit/AI tests, all `35` frontend tests, production frontend build, Python compilation, and clean diff integrity; no live provider calls or deployment occurred

24. `2026-09-10`
- `P4-D` lawful-ingestion preparation advanced but remains open: autonomous discovery no longer publishes from AI confidence alone, and every promoted candidate is held unpublished and unverified until separately obtained statutory and source evidence satisfies the publication gate
- canonical identity handling now normalises ABN, Australian E.164 phone, website domain, and business name; duplicate matching includes the required fuzzy local fallback, while `db.delisted_entities` blocks matching ABN, phone, or domain identities from re-ingestion
- configured public-source scanning identifies as `DTD-Bot/1.0`, enforces at most one request per two seconds per domain, bounds HTML responses, records source timestamps and SHA-256 evidence, and retains bounded source-failure suppression
- the seeding CLI now computes the canonical quality score, keeps publication behind a separate authorised `--apply --publish-qualified` gate, distinguishes detected from persisted failures, and can write a machine-readable dry-run/apply manifest with deterministic run identity and the honest launch data gap
- `/ops` discovery evidence now counts suppressed candidates and raises a dedicated delisted-identity suppression case; source-health failure and suppression-window visibility remains in System Activity
- validation passed: `237` backend unit/AI tests, all `35` frontend tests, Python compilation, diff integrity, and a real zero-write dry run with an empty authentic dataset and a manifest reporting the remaining 100-profile gap
- no Google Places call, ABR call, website harvesting, live trainer creation, seed application, publication, provider mutation, or education-workspace interaction occurred; P4-D remains open for final source-specific adapter wiring and authorised-source configuration before any live harvest

25. `2026-09-10`
- `P4-D` provider preparation now includes bounded Google Places Text Search (New) and ABR Web Services adapters behind a checked-in, fail-closed source-use approval registry; approval requires an explicit provider/use record, terms review date, and approver, while provider network access also requires the dedicated operator flag and matching credential
- the provider dry-run pipeline emits source states, credential presence without secret values, normalised source evidence, ABR verification evidence when an ABN is available, blocked reason codes, and an unconditional `publication_allowed: false`; it does not seed or publish trainers
- the ABR adapter now moves its provider request off the async event loop and can produce dry-run evidence without requiring a Mongo cache connection; successful configured runtime use still retains the existing bounded cache when Mongo is available
- deterministic validation passed: `70` focused provider/P4-D/ABR tests, `243` in-process backend unit/AI tests, Python compilation, and diff integrity; the real local dry run exited fail-closed with `source_terms_not_approved`, zero candidates, no network authority, an empty approval registry, and both provider credentials reported missing
- the legacy HTTP integration collection was not accepted as runtime evidence in this pass: its `32` failures and `9` setup errors were connection refusals because no backend was serving `localhost:8000`; no provider request, harvesting, trainer seed, publication, or production action occurred
- `P4-D` remains unaccepted until the owner supplies approved source-use records and credentials, the provider-backed dry-run evidence is verified under those approvals, and a separate explicit `E1` authorisation is granted before any live harvest or production seed

26. `2026-09-11`
- P4-D provider credentials are now locally present for both Google Places and ABR; the provider-manifest command loads the repository `.env` files and reports credential presence without exposing values
- the first Google Places key was exposed in an operator transcript and an untracked strategy document, so it was rotated immediately: the exposed key is deleted in Google Cloud, the replacement is active and restricted to `places.googleapis.com`, both ignored `.env` files contain the matching replacement, and no Google API-key pattern remains elsewhere in the workspace
- source approval remains the active fail-closed gate: `backend/data/ingestion_source_approvals.json` still contains zero approved records, so no further provider-backed dry run, harvesting, seed application, or publication is authorised by this credential configuration alone

27. `2026-09-11`
- the owner explicitly authorised the initial launch batch; P4-D source approval now covers public business facts from trainers' official websites and ABR name/ABN identity-status checks, while Google Maps/Places content is explicitly excluded from the persisted trainer dataset
- 20 Greater Melbourne trainer profiles were source-checked under `DTD-Bot/1.0` rate limits, matched to active ABR records, deduplicated, quality-qualified, seeded idempotently, and published as unclaimed profiles in the local DTD database; ambiguous, inactive, identity-mismatched, and Sydney-only candidates were excluded
- the launch batch is reproducible through `scripts/build_initial_trainer_batch.py`, `backend/data/melbourne_trainers_seed.json`, and machine-readable dry-run/apply manifests; the launch baseline is 20 and the supply-expansion gap is 80 toward the 100-profile target
- the canonical domain matcher now requires an exact hostname boundary, existing qualified unclaimed records can be safely enriched and published without overwriting owner-submitted/claimed context, active ABR evidence is retained without exposing private ingestion evidence publicly, and successful source-health rows are visible in `/ops`
- the invalid self-referential discovery source was disabled and retained as a cleared audit row; final live local verification showed 20/20 batch profiles in `/api/trainers`, no ABR/source evidence in public payloads, 21/21 healthy source rows in `/ops`, 20 active-ABR source rows, and zero source-ingestion exception cases
- validation passed: 27 focused P4-D tests, 247 in-process backend tests, Python compilation, `git diff --check`, clean dry-run/apply manifests, and direct authenticated API/Ops checks; the separate legacy HTTP collection produced 27 passes and 14 expected target-state mismatches against retired intro-fee/admin response contracts after its required server was supplied
- the initial P4-D launch packet is accepted locally; no Cloud Run/Firebase deployment occurred, and the remaining P4-D work is expansion from 20 to 100 authentic profiles plus production rollout under the later R1 gate

28. `2026-09-11`
- owner priority changed to launching the main DTD website first with the accepted attributable trainer supply and working trainer-submission path; expansion from 20 toward 100+ profiles is no longer a launch prerequisite
- the canonical acquisition plan now uses one pipeline in launch and post-launch modes: accepted official-website/ABR evidence for the launch baseline, then a separately licensed business-discovery feed feeding the same extraction, ABR, dedupe, suppression, quality, publish/hold, and `/ops` controls
- Sensis/Thryv SAPI, a successor API, or a scheduled feed is the preferred post-launch discovery direction, but the supplier enquiry is still pending and no contract, written retention/display/SEO/AI/outreach rights, schema, credential, pricing, adapter, or production approval exists
- MacroMatch and TotalCheck are recorded as validation/cleansing/enrichment products rather than initial discovery sources; they must not be substituted for SAPI without an explicit supplier grant for the required discovery use
- Google remains the runtime and factual-structuring ecosystem, but Google Places/Maps content and Gemini Search Grounding are excluded from persistent trainer acquisition; Gemini may structure only content from URLs DTD obtained lawfully, and AI confidence alone never authorises publication
- the first Cloud Run revision failed before binding to port `8080`; startup-log diagnosis and a healthy replacement revision remain the immediate deployment blocker

29. `2026-09-11`
- Cloud Run startup failure diagnosed from logs: `dtd-mongo-url` secret in Secret Manager pointed to `mongodb://localhost:27017`; during startup index creation, PyMongo timed out (30s), raising an unhandled exception before Uvicorn could bind to `${PORT:-8080}`, failing Cloud Run's STARTUP TCP probe
- backend hardened against database connection delays: added `_ensure_indexes()` with `asyncio.wait_for(timeout=10.0)`, configured `AsyncIOMotorClient(serverSelectionTimeoutMS=5000, maxPoolSize=15, minPoolSize=1)`, wrapped lease heartbeat probe in try/except, added root `/` and `/health` endpoints, and verified with `backend/tests/test_startup_resilience_unit.py`
- validation passed: all 225 backend unit tests passed in 0.41s, local Uvicorn on port 8080 passed `/health`, `/api/health`, `/api/config`, and `/api/trainers` (39 public trainers returned), 35 frontend tests passed, frontend production build passed
- Cloud Run backend deployed to service `dtd-api` in region `australia-southeast1` on project `gen-lang-client-0028123502` using Secret Manager references; live endpoints `https://dtd-api-870311309192.australia-southeast1.run.app/` and `/api/` return HTTP 200 `{"service":"dog-trainers-directory-match-engine","ok":true}`
- Firebase Hosting configured for site `gen-lang-client-0028123502` with SPA rewrite `{"source": "**", "destination": "/index.html"}`; frontend deployed to `https://gen-lang-client-0028123502.web.app` (182 files released); direct SPA routes `/trainers`, `/submit`, `/privacy`, `/terms`, `/ops`, `/how-it-works` verified returning HTTP 200
- custom domains `dogtrainersdirectory.com.au` and `www.dogtrainersdirectory.com.au` registered on Firebase Hosting; required DNS target `199.36.158.100` and ACME challenge tokens obtained
- Playwright Chromium and Headless Shell installed locally; Playwright end-to-end verification script `scripts/verify_frontend_browser.py` executed across desktop (1280x800) and mobile (390x844) viewports
- identified and resolved CORS header delimiter mismatch (pipe `|` vs comma `,` from gcloud env flags) and wrapped `/api/config` and `/api/trainers` with DB-delay fallbacks in `backend/server.py`; unit tests verified in `test_startup_resilience_unit.py`
- updated Cloud Run service to revision `dtd-api-00004-8tp` (serving 100% of traffic); verified CORS preflight and live `/api/config` returning HTTP 200 with credentials enabled; re-ran Playwright test suite and verified 0 console errors across all pages and viewports with full visual screenshot artifacts preserved
- automated migration script `scripts/sync_to_atlas.py` created to stream local MongoDB collections (43 published trainers, 20 ABR-verified) to Atlas, update Secret Manager `dtd-mongo-url`, restart Cloud Run revision, and verify health
30. `2026-09-11`
- MongoDB Atlas cluster `DTD` resumed by owner (`state: IDLE, paused: False`); executed `scripts/sync_to_atlas.py` streaming all 45 local MongoDB trainer records and associated system collections into Atlas
- Secret Manager `dtd-mongo-url` updated with authenticated Atlas SRV URI; Cloud Run `dtd-api` restarted and verified live: `/api/health` returned HTTP 200 `{"ok":true,"service":"dog-trainers-directory-match-engine","database":"available"}`
- live trainer directory verified on Cloud Run: `GET /api/trainers` returned 39 active listings; acquired profile `13a3eb2c-d0e2-4812-87a1-bdebfb641879` (Positive K9 Training, ABN verified) verified returning full public profile
- end-to-end launch journey proven with synthetic test submission:
  - `POST /api/submissions` persisted submission `6f648888-96cb-4d81-803d-af2cbc5ebbdf` in state `held` (`verification_status: unverified`, `abn_status: invalid_checksum`)
  - submitter notification email dispatched via Resend (`submitter_notification_status: sent`)
  - test trainer `76ae68ed-4784-4805-924f-c02cfb42c36c` persisted as `published: false` and strictly excluded from public directory
  - `/ops` oversight verified: `integrity.live_total: 43`, `integrity.hidden: 3`, `submissions_summary.auto_held: 5`
- visual Playwright verification re-executed with live Atlas data: captured screenshots for homepage, directory (39 trainers), acquired trainer detail (`/t/:id`), submit form, and `/ops` with 0 console errors
31. `2026-09-11`
- Gemini API key populated from GCP project `gen-lang-client-0028123502` and verified live with `google-genai` 2.22.0 (`gemini-3.6-flash` responding `pong`); `GEMINI_MODEL=gemini-3.6-flash` set in environment
- In-zone Vercel DNS cutover executed cleanly via Vercel CLI:
  - `@` A record pointed to `199.36.158.100` (`rec_39ed1e8ea32cc0a0570b1d5f`)
  - `www` CNAME record pointed to `gen-lang-client-0028123502.web.app.` (`rec_d1ff586e9e948c42ee34038a`)
  - `@` TXT record added for Firebase hosting verification (`rec_61debb879abfe84d44a786a3`)
  - `_acme-challenge` TXT records added (`rec_f695c665c30be24998501101`, `rec_220ccfa8cc8eda5b88744880`)
  - DNS propagation verified via `dig`: `199.36.158.100` and ACME challenge tokens resolving live; zero impact on Zoho Mail or Resend
- Profile enrichment script `scripts/enrich_profiles_gemini.py` updated to modern `google-genai` SDK and executed across 31 candidate profiles:
  - 18 profiles enriched with public phone numbers, contact emails, and bios
  - 9 aggregator URLs held without fabrication
  - 4 stale/dead domains logged
  - Full provenance evidence saved to `backend/data/enrichment_run_log.json`
- Synchronized all updated profiles and collections to MongoDB Atlas via `scripts/sync_to_atlas.py`; restarted Cloud Run and confirmed healthy `/api/health` returning `database: available`
- All changes committed and pushed to `https://github.com/carlsuburbmates/dtd.git` (`dbb3217`)

32. `2026-09-12`
- Conducted comprehensive audit of `https://dogtrainersdirectory.com.au/trainers` across desktop and mobile viewports using native browser subagent, DOM inspection, and network profiling.
- Identified and remediated critical production data issues:
  - Purged 10 integration test listings (`Activation Test Trainer`, `Test Trainer Verify`) by setting `published: false`, `status: 'suppressed_test'` via `scripts/clean_and_slugify_trainers.py`.
  - Repaired 3 mangled IDs ending in `:t` (`Urban Paws Melbourne`, `Dog Force 1`, `Melbourne K9 Force`).
  - Populated unique, human-readable SEO slugs across all 34 authentic Melbourne dog training businesses (e.g. `/t/urban-paws-melbourne`, `/t/northside-recall-school`).
  - Streamed cleaned collection to MongoDB Atlas cluster `DTD` via `scripts/sync_to_atlas.py`.
- Fixed search, filtering, and taxonomy defects:
  - Updated category filter in `backend/server.py` to match behavioural synonyms and bio descriptions (`category=reactivity` now surfaces 17 qualified trainers instead of 0).
  - Re-deployed Cloud Run revision `dtd-api-00008-9wc` serving 100% of traffic.
  - Renamed misleading primary navigation item in `PublicChrome.jsx` from "For trainers" to "Find a trainer".
  - Added reactive document title (`Find a Dog Trainer in Melbourne | Dog Trainers Directory`) and an instant "✕ Reset filters" control in `Trainers.jsx`.
  - Updated `public/index.html` meta description removing stale "prelaunch" wording.
  - Corrected business name truncation bug in `TrainerDetail.jsx` (`trainer.name` instead of first-name `.split(" ")[0]`).
  - Hardened `frontend/src/lib/api.js` with `frontend/.env.production` fallback preventing compile-time `localhost:8000` leaks in production builds.
  - Built and deployed updated frontend bundle to Firebase Hosting; live end-to-end browser verification passed with 0 test listings, active reactivity filtering (17 trainers), clean slug storefront navigation, and 0 console errors.

33. `2026-09-12`
- Executed comprehensive multi-route frontend audit across desktop and mobile on `https://dogtrainersdirectory.com.au` (`/`, `/submit`, `/how-it-works`, `/pricing`, `/trust`, `/faq`, `/contact`, `/melbourne/richmond`, `/about`, `/privacy`, `/terms`).
- Hardened Homepage matching diagnostic intake against Minified React Error #31:
  - Sanitized `matches` payload in `Home.jsx` on receipt, coercing `id`, `name`, `suburb`, and `match_reasoning` to pure strings.
  - Guarded match rendering with `{typeof m.match_reasoning === "string" ? m.match_reasoning : ""}` and defensive fallback keys `<article key={m.id || ...}>`.
  - Created dedicated unit test suite `frontend/src/pages/Home.test.jsx`.
- Polished `/submit` onboarding and validation user experience in `Submit.jsx`:
  - Added high-visibility validation error banner at top of form (`data-testid="submit-validation-summary"`).
  - Implemented field-level inline error messages and red border highlights (`border-rose-400 focus:border-rose-500 bg-rose-50/20`) on empty required fields.
  - Added styled highlight treatment and guidance messages for unaccepted statutory consent checkboxes.
  - Added dynamic error clearing as user enters data or toggles consents.
  - Created dedicated unit test suite `frontend/src/pages/Submit.test.jsx`.
- Corrected American vs Australian English copy inconsistencies across `About.jsx`, `Contact.jsx`, `HowItWorks.jsx`, `Pricing.jsx`, and `Terms.jsx` ("behavioral" -> "behavioural", "billing inquiries" -> "billing enquiries").
- Verified complete test suite: all 10 frontend test suites (38 unit tests) passed; production build compiled cleanly (`npm run build`).
