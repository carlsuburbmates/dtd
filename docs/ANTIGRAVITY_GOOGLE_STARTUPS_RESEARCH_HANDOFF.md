# Antigravity Handoff — Google for Startups Cloud Program Review

**Prepared:** 23 October 2026
**Requested work:** independent, evidence-led research and recommendations for improving the existing Google for Startups Cloud Program application/review.
**Mode:** read-only research. This is not implementation or permission to contact Google.

## Initial prompt for Antigravity — do this first

Before assessing DTD or recommending an application action, independently build a current, end-to-end understanding of the Google for Startups Cloud Program from its official sources. Treat prior assistant summaries and this case brief as leads to verify, not as the program's source of truth.

Research the relevant program surface, not only the Start tier:

- Program overview, tiers and benefits, including pre-funded Start, funded Scale, AI-specific benefits, and any other tier applicable to a bootstrapped technology startup.
- Current eligibility and exclusions; how Google describes a technology/digital-native startup, working MVP, business model, fundraising intent, "founded" date, sole-trader businesses, marketplaces/directories, and service businesses.
- Funding definitions and evidence, prior Google Cloud credit limits, free-trial treatment, application fields and evidence, domain/email/billing identity matching, and how credits are assigned and used.
- Application review timelines, manual review, website verification, action-needed/re-review/reapplication routes, official support channel, and any relevant terms for the credit or Workspace benefits.
- Any other official requirement that could materially affect this application. Do not broaden into unrelated Google products or perks unless they change the decision.

Use current primary Google sources and any directly relevant Australian government business-register sources. Record the access date and exact source URLs, distinguish direct requirements from interpretation, and mark ambiguity instead of filling gaps with assumptions. Use only short quotations where necessary.

Maintain the reusable findings as a durable, dated baseline at `docs/GOOGLE_FOR_STARTUPS_PROGRAM_BASELINE.md`. Keep that baseline focused on general program rules and source links; separate official requirements, interpretations, evidence standards, and unresolved questions. Add a short change log and update it when official terms change or a later task verifies a stale point. Add it to `docs/README.md`. Do not put the owner's ABN number, personal address, credentials, billing identifiers, private application correspondence, or account-specific evidence in this general baseline. Keep DTD-specific evidence in this handoff or another appropriately scoped, sanitized case record. Work locally and report the exact files changed; do not commit or push.

Only after establishing this baseline, apply it to DTD's verified facts and produce the case-specific verdict and recommendations required below. Do not send email, submit/reapply, publish site changes, or change account/provider state.

## Objective

Assess the strongest truthful route for Dog Trainers Directory (DTD) to obtain approval for Google for Startups Cloud credits. Independently verify the application history, current official program criteria, business/product evidence, domain and billing alignment, and the website-verification issue. Return ranked recommendations and a fact-checked response strategy for the program team.

Do not optimize for approval by inventing or overstating facts. If the owner or provider evidence does not support eligibility, say so and recommend the smallest legitimate next step.

## Authority and boundaries

- Use authenticated, existing local sessions and read-only provider access where useful. Re-check the account and mailbox actually in use before relying on a view. Do not request, expose, copy, or store passwords, OTPs, recovery codes, cookies, tokens, ABN number, personal address, or billing identifiers in chat, this handoff, or repository documentation.
- Application correspondence was addressed to `info@dogtrainersdirectory.com.au`. The owner corrected that the active Zoho login is `admin@dogtrainersdirectory.com.au`. Previous browser evidence showed the `info@` inbox; the connected Zoho API surfaced `admin@` and did not return the older application thread. Treat this as a mailbox/scope reconciliation task. Do not assume the alias, mailbox, browser session, and connector account are interchangeable.
- The owner supplied these facts: **no Google for Startups credits were received previously; no equity funding has been raised; the ABN is held in the owner's personal name.** The owner has not yet confirmed whether they genuinely plan to seek institutional venture funding soon. Do not infer that intention.
- Read the current working tree before relying on old notes. Reuse valid prior evidence, but refresh dynamic facts and label each as **verified now**, **prior-session evidence**, **owner-stated**, **inference**, or **unknown**.
- Do not modify or publish the public site, alter production/sandbox configuration, change billing or account settings, submit/reapply to a program, send/reply to email, book a sales call, accept terms, or transmit personal/business identifiers. Provide recommendations and optional proposed wording only. Stop at any action-time confirmation or new owner authority gate.
- Do not start unrelated DTD roadmap work. Follow repository `AGENTS.md`, `.codex/skill-policy.toml`, and the DTD evidence and release boundaries.

## Known evidence to verify and reconcile

### Application and mail history

The application mailbox is `info@dogtrainersdirectory.com.au`.

- **11 September 2026:** Google for Startups first-step completion notice.
- **12 September 2026:** full application receipt. It says Google expected to provide a status in a few business days and that approved credits would be applied to the Cloud Billing Account ID entered on the application.
- **14 September 2026:** Mir Zishan Ali outreach inviting a 15-minute sales call. This is not an application decision or approval.
- **16 September 2026:** program-team “[Action Needed] Dog Trainers Directory: Google for Startups Cloud Program Update” from `cloudstartupsupport-noreply@google.com`, with Reply-To `cloudstartupsupport@google.com`. It says the team could not verify the supplied company website and suggests the URL may not load, may not match the company, or may lack enough company/product information. It invites a reply when public materials are available or a reapplication.
- Prior inbox searches, including Spam and Trash, found no subsequent approval, credit award, or program-team re-review. Re-run the targeted history search in the correct mailbox and report the search scope/results rather than generalizing beyond it.
- The owner completed Google's re-verification in Chrome in the prior session. A prior Cloud Console credits view showed only ordinary Free Trial credit and no Google for Startups award. The precise billing account ID submitted on the application was not recovered, and the Zoho API connection's `admin@` scope did not expose the older `info@` application mail. This does **not** establish the state of every billing account; reconcile the actual application ID to the intended account before making a stronger claim.

### Business, product, and funding evidence

- The official ABR record previously inspected matched the owner name and showed an active **Individual/Sole Trader** ABN beginning **26 August 2026**. Keep the identifier and personal details out of this report. The record's start date supports age eligibility but is not, by itself, proof of the startup's actual founding date.
- The DTD Git repository's initial commit is dated **17 April 2026**. This is evidence of product development within Google's 24-month Start-tier window for the September 2026 application, not definitive evidence of the legal or business founding date.
- DTD is a live dog-trainer discovery directory and guided matching product focused on Greater Melbourne. Repository plans describe a technology-led matching/discovery service, a product roadmap, and an owner/trainer marketplace model. Independently verify live capabilities and public evidence before using them in a response.
- DTD's stated model is free use for dog owners; trainers can use free core listings and optional paid visibility/subscription products. Production checkout is fail-closed (`ENABLE_TRAINER_BILLING_CHECKOUT=0`). No revenue, paying-customer, user-growth, or traction claim has been verified for this application; do not invent one.
- AI is assistive/advisory in the current product direction. The evidence does not support positioning DTD as an **AI-first** company. Do not claim AI-first credits or benefits.
- Do not describe the sole trader as an incorporated company or imply the ABN is a company number. Assess whether Google's current terms accept this legal form and whether its business/product criteria are met; if not answered by official material, ask program support in the proposed response.

### Website and reviewer visibility

- Finding **DF-054** in `docs/DTD_CURRENT_STATE.md` records the prior check: unauthenticated requests to `/` and `/about` returned HTTP 200 but the static HTML contained a generic title, a short meta description, an empty React root, and a JavaScript-required notice; the sitemap listed only `/`. The normal browser rendered the React application, including directory content. The fetch did not establish how Google's specific reviewer rendered the site.
- The meta description used “reviewed, verified dog trainers”; DF-016 records a concern that some trust language may exceed the available evidence. Re-check current public copy and avoid repeating unsupported trust, safety, verification, scale, or outcome claims.
- Independently re-test the root, `www`, `/about`, sitemap, canonical/robots behavior, and representative product pages. Compare static response content with rendered browser content. Do not assume the previous result is current or that Google uses the same rendering path.
- A prior production evidence note says the Firebase Hosting frontend and Cloud Run API are deployed on the DTD domain. Reconfirm only what is necessary for this application review; do not touch production.

## Official program sources to refresh

Start with Google's current primary sources and record access date and exact wording relevant to this case:

- [Google for Startups Cloud Program benefits and eligibility](https://cloud.google.com/startup/benefits)
- [Google for Startups Cloud Program FAQ](https://cloud.google.com/startup/faq)
- [Google pre-funded startup tier](https://cloud.google.com/startup/pre-funded)
- [Australian Business Register / ABN Lookup](https://abr.business.gov.au/)

Verify, rather than assume:

1. Whether Start still requires a technology/digital-native startup, working MVP, clear business model, plans to seek venture funding soon, founding within 24 months, no previous Google Cloud credits beyond Free Trial, and roadmap/market-disruption evidence.
2. Whether no equity raised is compatible with Start and only rules out Scale; distinguish current funding from a genuine future fundraising plan.
3. How Google defines “founded” for an individual/sole-trader business and what evidence is accepted.
4. Whether a sole trader/ABN-backed business can qualify and how it should be represented in application fields.
5. Exact website, business email, organization, and billing-account matching rules; identify the submitted 18-character billing ID only if it can be read from authorized first-party records. Never guess it.
6. Whether there are current free-trial, prior-credit, paid-Google-Workspace, domain-age, or reapplication restrictions relevant to this exact application.
7. The official process for asking for re-review versus submitting a new application after a website-verification issue.
8. Any eligibility risk from DTD being a directory/marketplace, whether it could be viewed as a traditional small business, agency, or service business, and what truthful evidence distinguishes the actual software product from those excluded categories.

## Research instructions

1. Inspect current repo state and the focused authority documents: `AGENTS.md`, `.codex/skill-policy.toml`, `docs/README.md`, `docs/DTD_CURRENT_STATE.md` (especially DF-016 and DF-054), `docs/DTD_END_TO_END_PRODUCT_AND_BUSINESS_ROADMAP.md`, `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md`, `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` (especially CDR-014), and `docs/specs/MONETISATION_AND_PRICING.md`. Do not inspect `archive/` unless the owner separately asks for archival research.
2. Independently inspect the correct Zoho mailbox and relevant Google Cloud billing/credits view using existing authenticated sessions. Separate mailbox identity from the application recipient and separate Google identities, organizations, projects, and billing accounts. Do not alter state.
3. Confirm whether the public site now provides enough crawlable company/product information and whether the website, submitted business email, and intended billing account align. Distinguish an actual technical cause from Google's stated possible causes; do not claim the website caused rejection unless evidence supports it.
4. Verify program eligibility against current official Google criteria. Use ABR only for identity/status and age evidence; do not expose the ABN. Avoid unsupported inference from repository dates, software architecture, or owner statements.
5. Assess the strongest truthful product/company narrative, including product stage, working MVP evidence, differentiation, roadmap, business model, use of Google Cloud, and market opportunity. Identify what is publicly verifiable now versus what would require new publication or owner evidence.
6. Research any viable no-equity/Start route and only relevant alternatives. Do not encourage fundraising merely to obtain cloud credits, and do not recommend saying the owner plans to raise if they do not.

## Required handoff back

Return a concise but complete research memo with:

1. **Verdict:** likely eligible / conditionally plausible / unlikely under the current facts, tier, confidence, and the exact requirement that controls that verdict.
2. **Evidence matrix:** each material criterion, evidence source/date, status (`verified now`, `prior-session evidence`, `owner-stated`, `inference`, `unknown`), and what would close an unknown.
3. **History reconciliation:** application timeline, exact unresolved message/decision state, mailbox/account search scope, and whether any approval or credits were found.
4. **Reviewer-fix assessment:** current public site evidence, whether the prior DF-054 issue persists, priority website content/technical corrections, and any DF-016 wording risk. Recommend changes only; do not implement or publish them.
5. **Billing and identity reconciliation:** whether the application billing account is identifiable and matches the company/domain; state the safe verification route if not. Redact IDs in the report.
6. **Recommended response path:** reply to the existing program-support thread or reapply, with rationale. Include optional fact-checked draft wording addressed to the official program-support thread, but do not create/send it.
7. **Minimal owner questions:** only facts that cannot be established locally or from authorized records. At minimum, resolve whether the owner genuinely intends to seek institutional venture funding soon and the expected timeframe; do not ask again for no-equity or no-prior-credit facts already supplied.
8. **Risks and next actions:** rank actions by likely impact and evidence strength; distinguish what can be fixed locally from public or provider actions needing separate authorization.

For any proposed implementation or public communication, stop after the research memo and return the exact scope, copy/change, affected surface, and verification plan for a separate owner-authorized package. Do not push, deploy, change Google/Zoho state, submit an application, or send a message.
