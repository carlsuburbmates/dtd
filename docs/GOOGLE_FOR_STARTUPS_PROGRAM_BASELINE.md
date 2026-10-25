# Google for Startups Cloud Program — Baseline Requirements & Rules

**Document Version:** 1.0  
**Baseline Date:** 23 October 2026  
**Scope:** Reusable, program-level baseline for the Google for Startups Cloud Program based directly on official Google Cloud documentation and standard business registry principles.  
**Sanitization Notice:** This baseline contains exclusively general program rules, verified criteria, and official source links. It contains no account-specific credentials, billing identifiers, personal addresses, ABN numbers, or private correspondence.

---

## 1. Official Primary Sources

The following official primary sources were accessed and verified on **23 October 2026**:

1. **Google for Startups Cloud Program — Eligibility & Benefits:**  
   [https://cloud.google.com/startup/benefits](https://cloud.google.com/startup/benefits)
2. **Google for Startups Cloud Program — Frequently Asked Questions (FAQ):**  
   [https://cloud.google.com/startup/faq](https://cloud.google.com/startup/faq)
3. **Google for Startups Cloud Program — Pre-Funded Startups (Start Tier):**  
   [https://cloud.google.com/startup/pre-funded](https://cloud.google.com/startup/pre-funded)
4. **Australian Business Register (ABR) / ABN Lookup:**  
   [https://abr.business.gov.au/](https://abr.business.gov.au/)

---

## 2. Program Structure, Tiers & Benefits

Google organizes the Google for Startups Cloud Program into distinct tiers matching startup maturity:

### 2.1 Start Tier (Pre-Funded / Bootstrapped)
Designed for early-stage digital-native technology startups building their MVP and preparing for scale and funding.

- **Cloud Credits:** Up to **$2,000 USD** in Google Cloud Platform credits, valid for 12 months.
  - Credits cover core GCP services (Compute, Cloud Run, Firestore, BigQuery, etc.) and proprietary Google AI models (Gemini, Gemma via Vertex AI / AI Studio).
  - Third-party models on Model Garden / Marketplace are billed directly and are **not** covered by program credits.
- **Productivity & Collaboration:** **12 months free Google Workspace Business Plus** for new signups.
  - *Condition:* The company domain must not have been subscribed to a paid Google Workspace plan within 31 days prior to applying, through the day the benefit is requested. Cannot be applied to existing annual commitments.
- **Developer & AI Enablement:**
  - Free tier Google AI Studio access.
  - **$200 USD** in Google Skills credits for technical training.
- **Perks:** Preferred partner discounts and access to Google startup events and webinars.

### 2.2 Scale Tier (VC-Funded)
Designed for venture-backed startups ready to expand infrastructure.

- **Cloud Credits:** Up to **$200,000 USD** over 2 years (or up to **$350,000 USD** for AI-first startups).
  - *Year 1:* 100% coverage up to $100,000 USD ($250,000 USD for AI-first).
  - *Year 2:* 20% coverage up to an additional $100,000 USD.
- **Support & Services:**
  - Up to $12,000 USD in Google Cloud Enhanced Support credits (1-hour response SLA).
  - Dedicated Startup Success Manager and Google Cloud Startup Customer Engineers.
  - $500 USD in Google Skills credits.
  - $600/month in Google Maps Platform usage credits (requires separate application).

### 2.3 Specialized Tracks
- **AI-First Track:** Must have AI built into the startup's foundational architecture and strategy (not merely a bolt-on or API wrapper). Offers enhanced credits up to $350k in the Scale tier.
- **Web3 Track:** Up to $200k over 2 years for Google Cloud and Firebase, Foundation grants, and Web3 perks (accepts verifiable token raises and foundation grants).

---

## 3. Detailed Eligibility Criteria (Start Tier)

To qualify for the **Start Tier**, an applicant must satisfy all of the following requirements:

| # | Official Criterion | Exact Requirement & Wording | Verification & Interpretation Standards |
|---|---|---|---|
| **C1** | **Startup Nature** | "Digital-native technology startups with a working MVP, a clear business model, and plans to seek venture funding soon." | Must be a software/technology product company. Excludes traditional brick-and-mortar small businesses, dev shops, consultancies, and service agencies. |
| **C2** | **Working MVP** | Must have a "working MVP" and "demonstrate a well-defined product roadmap and a clear vision for market disruption." | The product must be demonstrable online. Conceptual ideas without an accessible product or prototype do not qualify. |
| **C3** | **Fundraising Intent** | Must have "plans to seek venture funding soon." | The program is intentionally positioned as a feeder for high-growth, venture-backable ventures. While pre-funded startups need no current equity, Google expects an intention to pursue institutional/venture funding. |
| **C4** | **Company Age** | "Founded within the last 24 months." | Google publishes the 24-month criterion but the cited program pages do not define how it determines a sole trader's founding date. An ABN registration date, by itself, is not established here as Google's accepted date. Ask the program team which date/evidence applies to this application. |
| **C5** | **Prior Cloud Credits** | "Not yet received Google Cloud credits (beyond the free trial)." | Startups that previously received Google for Startups or partner credits are ineligible for a second award at the Start tier. Standard $300 Free Trial credits do not count against this limit. |
| **C6** | **Domain and Billing Alignment** | Have an 18-character billing account ID. The business email in the application must match the startup website domain, and the website domain must also match the email domain associated with the billing account. | This is stated in Google's [FAQ](https://cloud.google.com/startup/faq). The FAQ does not specifically require a Google Cloud Organization as the mechanism; it does require the billing account's associated email domain to match. Verify the actual billing account association before claiming alignment. |

---

## 4. Program Exclusions

Google explicitly excludes the following entity types across all tiers:
1. Consultancies, professional service agencies, dev shops, or digital marketing agencies.
2. Traditional small businesses (local service providers, sole traders without a scalable technology product).
3. Personal blogs, content sites, or affiliate sites.
4. Companies that have completed an IPO or been acquired.
5. Educational institutions, government entities, and non-profit organizations.
6. Cryptocurrency mining operations or token projects non-compliant with local regulations.

---

## 5. Evidence Standards & Technical Verification Expectations

### 5.1 Website and Reviewer Verification
- Google says the application business email must match the startup's public website domain and requires a working MVP and clear business model/product roadmap for Start tier. The program pages do not describe its crawler, URL-fetching, or website-review implementation.
- A server-rendered or static HTML response with concise, accurate product information is a practical way to make the site inspectable when JavaScript is unavailable. Treat this as a technical recommendation, not a published Google eligibility rule or a guarantee that a review will pass.
- Keep public claims about product behavior, customer outcomes, credentials, legal entity, and infrastructure within the evidence actually available. A readable page does not itself prove MVP acceptance or program eligibility.

### 5.2 Legal Entity & Australian Business Structure
- Google's published Start-tier criteria do not require prior equity funding; they do require a digital-native technology startup with a working MVP, clear business model, and plans to seek venture funding soon. Scale tier requires qualifying recent startup equity funding. See the [official tier comparison](https://cloud.google.com/startup/benefits).
- The pages cited here do not decide whether a particular Australian sole trader/ABN qualifies, what date counts as “founded,” or what corporate structure Google accepts for this application. The founder's ABN in their own name and absence of equity are case facts to present accurately and ask Google to assess; do not infer rejection or acceptance from them alone.
- Any future incorporation or investment structuring is a separate business/legal decision, not a Google Start-tier prerequisite stated in these sources.

### 5.3 Billing Account
- Google's FAQ says to have the **18-character Google Cloud billing account ID** ready and states that the company website domain must match both the application email domain and the email domain associated with the billing account. It does not name an Organization as the required mechanism for that association. Verify the exact submitted billing ID and associated email privately; never place either in this reusable baseline.

---

## 6. Review Process, Support & Reapplication Routes

- **Initial Timeline:** Google's FAQ says most applicants are informed within a few business days; applications requiring further manual review may take 10 days or more. This is an estimate, not a service guarantee.
- **Action Needed Notices:** Sent from `cloudstartupsupport-noreply@google.com` with a designated `Reply-To: cloudstartupsupport@google.com`.
- **Resolution Channel:** Google explicitly directs applicants with verification blockers, rejection questions, or re-review requests to reply directly to `cloudstartupsupport@google.com` or consult their assigned Google Cloud representative.
- **Reapplication vs. Re-Review:**
  - Replying to the existing `[Action Needed]` thread with evidence/clarification maintains application continuity and allows the reviewer to update the original case without creating duplicate billing associations.
  - Submitting a brand-new application is recommended only if the original case is formally closed or if requested by the support team.

---

## 7. Change Log

| Date | Author / Agent | Changes Made |
|---|---|---|
| 2026-10-23 | Antigravity AI | Initial establishment of verified Google for Startups Cloud Program baseline from official sources (FAQ, Benefits, Pre-Funded tiers). |
