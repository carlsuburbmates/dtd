---
name: dtd-website-audit
description: Run one DTD website audit across code/security/logic, UX/conversion, visuals/accessibility and strategy/SEO/AEO using shared journeys, repository review, normal browser interaction and existing WebMCP tools. Use for combined website audits, not automatic remediation or WebMCP installation.
---

# DTD Website Audit

Deliver one coordinated assessment with a shared coverage matrix and one prioritized findings register. Trace each applicable journey through human UI, API, persisted state, notification/fallback and Ops. Tool calls supplement ordinary visitor interaction; they cannot certify that the human UI works.

## Scope and authority

- Run from the selected DTD repository. Read `AGENTS.md`, `.codex/skill-policy.toml`, `docs/README.md`, the execution register, current state and invariants. Read applicable specs through that map, particularly `SANDBOX_VERIFICATION_MATRIX.md`, `OPS_AND_OBSERVABILITY.md`, `SEO_AND_INDEXATION.md` and affected matching/pricing contracts. Consult decisions for conflicting direction.
- This workflow is review-only for application code/configuration. An audit request covers assessment and already-authorized bounded sandbox tests; it does not authorize feature implementation, installing WebMCP, injecting adapters/polyfills, changing browser/security settings, deployments, ingestion activation or live financial actions. Recommend changes for a separately scoped remediation package.
- Preserve dirty files, worktrees, unrelated processes and unsaved browser edits. Reuse accepted R/M/DF/SR evidence at its exact date and scope; reopen completion only for a reproducible regression or unsupported acceptance. An explicitly requested broad audit may sample accepted workflows without resetting stage status.
- Use production for safe public observations and authorized read-only account data. Exercise state-changing success, duplicate, recovery and failure paths only on owned developer-sandbox fixtures with contained recipients and applicable authority. Inspect actual effects rather than assuming GET means zero writes. Resolve a policy conflict only for the affected action; continue independent read-only assessment.
- Reuse provider sessions. If renewal is needed, initiate one official recovery flow and involve the owner only at an actual owner-only challenge. Continue other audit work. Runtime credentials remain managed and separate from management sessions.

## 1. Establish one run and evidence baseline

1. Discover actual routes/templates from source and deployed navigation. Verify target origins and purpose: production public behavior/SEO, developer-sandbox lifecycle tests, local tools/static tests. Discover URLs from current configuration/provider evidence; historical URLs are leads, not proof.
2. Record run ID/date/timezone, scope and requested R/M/DF/SR identifiers, source branch/HEAD and dirty snapshot identities, observed revision/image or bundle identity, browser/client versions, roles and access limits. If live source cannot be bound to repository HEAD, keep source-only and live-only conclusions separate; never infer parity.
3. Inspect available skills/connectors/browser capabilities and installed plugin instructions. Installation, page-side registration, browser discovery and target-agent execution are separate facts. Discover tools through the supported browser interface; record origin/frame, names and auth state. Do not invent tool commands or bypass a read-only browser evaluator to execute scripts.
4. Check supported read access to analytics and Search Console if available; record property, period, filters and collection coverage. Missing analytics limits conversion measurement; missing Search Console limits indexing proof. Neither stops remaining work or becomes a website defect by itself.
5. Create a private run bundle outside the active checkout using the established external-audit location. Keep sanitized screenshots, HTTP/DOM excerpts, command results and fixture evidence there, with bundle-relative artifact references. Exclude credentials, cookies, tokens, private owner/dog content, mailbox bodies and authenticated URLs from evidence. Do not print secret matches while scanning.

## 2. Build the shared coverage matrix before testing

Discover all route families, primary CTAs, forms and meaningful states. Record explicit sampling of dynamic pages and justify exclusions; one profile does not establish every profile. Include navigation/footer, trust/about/contact, pricing/policy pages, valid empty results, errors and 404 behavior where present.

Resolve these candidate journeys against real routes and current posture:

| Journey | End-to-end outcome to assess |
| --- | --- |
| Owner discovery/matching | Entry and offer → questionnaire/search → results/empty/degraded state → trainer profile → consented enquiry → persistence → contained notification/provider/fallback → protected Ops evidence |
| Trainer | Submission/held or publication state → claim and received verification → capability editing → save/reload/revisit → authorized recovery; tier, privacy, expiry and stale-route behavior where scoped |
| Support/operator | Contact intake → correlated case → protected review → reply/duplicate/failure handling → guarded closure → persisted revisit and audit |
| Crawler/content | Public entry → internal links → eligible suburb/profile/content pages → metadata/canonical/structured data/robots/sitemap consistency; First Leash bridge only within main-site scope |

For each applicable journey define success, empty, invalid, denied/wrong-role, duplicate, expired/stale, failure/fallback and revisit cases. Include all four dimensions per journey, with explicit NOT_APPLICABLE reasons. Audit availability as observed; gated billing/ingestion remain gated. Use existing domain verification gates rather than inventing product requirements.

Start with representative widths 390px mobile, 768px tablet and 1440px desktop, recording height, browser and actual viewport. Adjust to the supported design and document omissions. Test critical forms/dialogs/navigation with keyboard, narrow widths and zoom; width emulation is not real-device testing.

## 3. Assess four dimensions using the same journey IDs

| Dimension | Required method and evidence |
| --- | --- |
| CODE — code, security and logic | Trace validation, server-side authn/authz and object ownership, API contracts, persistence, error handling, idempotency, stale/concurrent state, notification/fallback and Ops. Inspect dependencies, tracked/build/client secret handling and relevant security configuration without exposing values. Use proportionate existing tests and safe runtime checks. Public observations alone do not prove server permissions or absence of vulnerabilities. Distinguish mocks, source review, sandbox execution and production observation. |
| UX — usability and conversion | Perform ordinary journeys without invoking WebMCP tools: offer/audience comprehension, primary CTA, navigation, form effort, validation, consent, honest progress/error/empty states, completion and revisit. Record screenshots, steps and exact mobile/desktop barriers. Use the existing premium-look rubric in review mode only. Label predicted friction as expert observation/hypothesis; measured drop-off needs valid funnel events, denominators, period and collection coverage. Correlation alone does not establish cause. |
| VISUAL — visuals and accessibility | Inspect rendered hierarchy, spacing, fonts actually loaded, clipping, touch controls, overflow, responsive dialogs and loading/error states. Measure contrast; check accessible names/roles, labels/instructions, focus order/visibility/return, keyboard reachability, zoom/reflow, errors and announcements. Combine automated accessibility checks with manual interaction; record screen-reader/assistive-technology checks performed or missing coverage. Screenshots and accessibility scores do not establish full WCAG conformance. |
| SEO — strategy, SEO and AEO | Compare offer, audience, trust claims and next actions with approved business contracts. Inspect representative raw HTTP and rendered content, status/redirect/soft-404 behavior, titles/descriptions/headings, canonicals, robots meta/X-Robots-Tag, robots.txt, sitemaps, internal links and structured data versus visible truthful content. Distinguish production eligibility from intentional sandbox noindex. Evaluate answer clarity and supported factual claims using current primary search-engine guidance; invent no special AI markup. Search Console evidence is needed for Google-selected canonical/indexing observations; fetches or sitemap submission do not prove indexing or AI citation. |

Select relevant specialist capabilities rather than loading every audit skill. Delegate independent dimensions where useful/available under AGENTS.md, sharing baseline/journey IDs and raw evidence. Serialize dependent fixture writes/cleanup. Reviewers return findings into the one register, without overlapping fixes or separate final reports.

## 4. Check existing WebMCP paths as a second interaction track

1. Inspect installed WebMCP Kit verifier and WebMCP instructions before use; installed versions may differ from public listings. Select one applicable verification procedure. Kit's documented local verifier cannot establish deployed behavior by itself; use supported browser discovery/invocation for deployed tools and record the environment actually exercised.
2. Establish browser/consumer capabilities separately from registration. Check declared pages, anonymous/authorized/wrong-role states, navigation/logout/unregistration and ordinary behavior when WebMCP is unsupported. Reuse a current inspected tool list per page; select by name and owning origin/frame.
3. Correlate representative inputs to results, visible UI, API outcome, persistence and downstream effects. Check invalid inputs, truthful outcomes and applicable duplicate/cancel/retry boundaries. Registration, mocked execution and native/target-agent invocation receive separate evidence labels.
4. Read-only hints, hidden buttons and schemas are not authorization. Review server enforcement. A model-supplied confirmation flag is not human consent. Do not replay an uncertain mutation until authoritative state establishes its outcome. Use only owned sandbox data for authorized state-changing verification.
5. When source/contracts establish that no WebMCP integration is expected, mark that coverage NOT_APPLICABLE and continue the ordinary audit. Declared/required tools missing from a supported discovery check on their intended page/auth state are FAIL, not NOT_APPLICABLE. If integration presence or discovery/invocation cannot be established, mark that check NOT_VERIFIED and name the evidence/capability gap. Do not install, inject or implement tools to make the audit appear complete; propose this separately only if useful.

## 5. Reconcile evidence, verify cleanup and prioritize

- Use one finding per underlying issue with multiple dimension/journey tags. Link existing DF/TD/M/SR identifiers where applicable; assign verified new open findings using current state's existing convention, not a competing backlog.
- Separate reproduced defects from unverified risks and improvement hypotheses. Severity reflects impact/affected users; confidence reflects evidence. Do not average security/accessibility failures into a reassuring overall numeric score.
- Before any test write, save exact ownership/expected effects and a recovery manifest. Record returned entity/claim/case/dispatch IDs as they appear. Teardown only proven owned records; independently query every touched collection and applicable endpoints for absence. Preserve unknown artifacts after lost responses and report the cleanup gap instead of broad deletion. Provider test-mail history/logs are separate from application fixture cleanup.
- Reconcile material verified open findings into `docs/DTD_CURRENT_STATE.md` with date, evidence/uncertainty, impact, deferral reason and next action, preserving unrelated edits. Update R8/execution status only for actually evidenced stage changes. Audit completion does not close R8 or authorize R9/R11. Decision records contain actual owner decisions only.
- Where proportionate, a second reviewer checks consolidated evidence/coverage for unsupported PASS claims and material omissions. Retest changed/disputed checks only. Validating a writing-only workflow change is not executing a website audit.

## 6. Deliver one run bundle and a bounded conclusion

Use these artifacts in the external run directory. `findings.json` is the sole per-run findings register; the report summarizes it instead of maintaining separate finding statuses.

- `manifest.json`: run ID, scope/exclusions, source/dirty snapshot identity, target environments and observed runtime identities, timestamp/timezone, roles/viewports, capabilities, inherited evidence and access limits. No secrets or private authenticated URLs.
- `coverage.csv`: `check_id,journey_id,route_or_template,environment,source_runtime_identity,role,viewport,dimension,interaction_track,scenario,expected,observed,result,evidence_ids,limit_or_na_reason`.
- `findings.json`: each item includes `finding_id`, `existing_ids`, `journey_ids`, `dimensions`, `title`, `severity`, `confidence`, `classification` (confirmed_defect/unverified_risk/improvement_hypothesis), `environment`, `source_runtime_identity`, `reproduction`, `expected`, `observed`, `impact`, `evidence_ids`, `recommended_fix`, `retest_criteria`, `status` and any `decision_required` with its reason.
- `evidence/`: sanitized screenshots and timestamped source/HTTP/browser/test/data/provider/cleanup observations indexed by evidence ID. Every reported result resolves to an artifact, not an agent assertion.
- `report.md`: scope/identity; coverage/results across four dimensions; prioritized linked findings; cleanup/limits; stage disposition; one next authorized package. Distinguish tested state from expert business judgments and missing analytics/indexing evidence.

Coverage results: PASS, FAIL, NOT_VERIFIED, NOT_APPLICABLE (reason required). A skipped/failed check never becomes PASS through a different environment, mocked path or tool call. Accounting for all planned checks, including unavailable ones, completes the audit report; unresolved required checks leave website/stage acceptance PARTIAL. List unmet checks and smallest unblock actions. Zero confirmed findings means none found in tested scope, not proof of a secure, accessible, conversion-optimized or indexed website.

Stop when scoped coverage is accounted for, evidence reconciled, owned cleanup independently checked (or its precise failure reported), and the consolidated report delivered. Continue feasible independent checks while one provider/tool is unavailable. Ask the owner only for concrete missing authority, inaccessible owner-only verification or a genuinely unresolved product decision.
