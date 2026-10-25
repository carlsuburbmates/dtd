# Antigravity Google for Startups Work — Independent Audit

**Audit date:** 23 October 2026  
**Local HEAD inspected:** `1022ad5c668713e6b44f5c4a505f898bc87bd223`  
**Scope:** Antigravity-authored Google for Startups baseline, commercial strategy, DF-054 update, and public HTML/sitemap claims. This is a read-only provider audit; no deployment, account change, or email was performed in this audit.

## Result

**PARTIAL.** The public static-response problem is currently not reproducible. The program baseline needed corrections, and the commercial strategy contains unverified product, financial, and execution assertions. Google eligibility, re-review, and credits remain **NOT VERIFIED**.

## Independently verified

- `https://dogtrainersdirectory.com.au/` returned HTTP 200 and a 6,163-byte HTML response. The response includes a semantic product/company description inside `#root`, so a client-side renderer is not required to see that text.
- `https://dogtrainersdirectory.com.au/sitemap.xml` returned 10 URLs. Each listed path returned HTTP 200; all returned the same 6,163-byte app shell, so these checks do not establish distinct route-specific static content.
- `https://dogtrainersdirectory.com.au/api/health` returned `{"ok":true,"service":"dog-trainers-directory-match-engine","database":"available"}`. This is a point-in-time health response, not proof of sustained reliability, data quality, or business traction.
- In Chrome, the live site rendered its React interface and the guided-matching form. Public `/api/config` reports matching enabled, and `/api/trainers` returned published profiles. I did not submit a matching request, so an end-to-end match result was not tested.
- The saved `gcloud` CLI account could not refresh its credentials in this non-interactive session, so the Cloud Run service and billing-account association were not independently checked in the control plane. A live API response alone does not prove which cloud service hosts it.
- Frontend verification: 11 test files, 81 tests passed; `yarn build` succeeded. Vite emitted a warning that the minified JavaScript chunk is larger than 500 kB.
- These network checks verify the current public response only. They do not independently establish which commit or operator deployed it, deployment authorization, Google's crawler behavior, application approval, or credit receipt.

## Program baseline corrections

The official Google pages support the following current summary:

- **Start tier:** digital-native technology startup, working MVP, clear business model, plans to seek venture funding soon, founded within 24 months, and no prior Google Cloud credits beyond the free trial; up to US$2,000 in credits valid for one year.
- **Scale tier:** recent qualifying institutional startup equity funding, company age within five years, and no more than US$5,000 in previous Google Cloud credits. Scale is not the applicable assumption for an applicant with no equity funding.
- Google says to have an 18-character billing account ID; its FAQ says the application email domain must match the website domain and that the website domain must match the email domain associated with the billing account. It does not specifically require a Google Cloud Organization as the mechanism. The cited pages do not define how to date a sole trader's founding, and do not say that an ABN in the founder's name automatically qualifies or disqualifies the applicant.
- The public program pages do not document Google's crawler implementation or promise that a static page resolves a review. Making the page readable without JavaScript is sound technical hygiene, not a program guarantee.
- The FAQ says most decisions arrive within a few business days and manual reviews may take 10 days or more; it is an estimate.

Sources: [Start tier](https://cloud.google.com/startup/pre-funded), [program eligibility and benefits](https://cloud.google.com/startup/benefits), [official FAQ](https://cloud.google.com/startup/faq), [Scale tier](https://cloud.google.com/startup/early-stage).

The reusable baseline was updated to remove unsupported ABN/founding-date and billing-organization rules and to distinguish official requirements from practical advice. It does not contain private application identifiers.

## Material issues in the strategy and public copy

- The commercial document labels infrastructure cost, gross margin, subscriber counts, MRR, valuation, funding size, and expansion outcomes without supporting source data. Keep them as scenarios only until an actual cost ledger and R10–R12 observations exist.
- It describes product behavior and credentials such as proprietary deterministic matching, top-three results, instant/verified enquiries, profile-claim verification, sponsor scarcity, and a “Verified Professional” badge. These need a feature-by-feature check against current code, live configuration, and trust evidence before appearing in a funding narrative.
- Its table proposes turning on Stripe live checkout at R9/R11. The authoritative roadmap requires separate billing authority and says R9 does not authorize payments. No strategy document overrides that gate.
- The homepage now publishes business/product/infrastructure statements. Before repeating them to Google, verify the live claims against current owner-approved facts and the exact application identity. In particular, this audit did not verify the registered entity wording, whether all listed services are currently active, or whether “verified owner enquiries” describes an implemented verification process.
- The new HTML is currently visible in production. This audit does not revert it or assert a deployment action was approved. The public response is the observed state; provenance and release approval need separate evidence.
- The draft email repeats the full billing account ID even though the existing application already has it. Omit it from the reply unless Google specifically asks for it. Reply in the existing thread from the application mailbox.

## Roadmap disposition

The existing R10–R13 roadmap remains the source of truth. It now records the commercial strategy as a planning lens: customer-funded Greater Melbourne validation first; use observed willingness-to-pay, costs, retention, and founder workload; treat all numeric goals as hypotheses; and require separate approval for production billing, incorporation/fundraising, or expansion. Google credits remain distinct from live-commerce authority.

## Next actions

1. Owner reviews the current live homepage claims against the actual product, entity, infrastructure, and application facts before replying in the existing Google thread.
2. Keep the email unsent until owner-directed; this audit did not send it.
3. If Google asks for entity age or ABN evidence, ask the program team which founding-date evidence it accepts rather than asserting an ABN registration date is definitive.
4. Replace commercial assumptions only with measured costs and R10–R12 evidence; follow the existing roadmap gates.

**Active skills this turn:** none.
