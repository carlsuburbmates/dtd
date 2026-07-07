# Complete Website Page Spec

Date: 2026-06-09
Scope: canonical page-level specification for the intended DTD website.

## Authority

This document is part of the canonical implementation pack.

Rules:
1. It defines the intended website and page-level behavior.
2. It does not claim that current code already satisfies every requirement.
3. If a lower-authority doc conflicts with this page spec, this page spec governs for page-level implementation.
4. `docs/design/WEBSITE_WIREFRAME_SPEC.md` may define structural layout and
   module order, but it must not override route purpose or behavior defined
   here.

## Locked website posture

This page spec is written for the current intended DTD website under the locked project truth:
1. Product: `DTD` / `Dog Trainers Directory`
2. Launch posture: `supply_first`
3. `PUBLIC_MATCHING_ENABLED=false`
4. Public live owner matching is not exposed from the home entry
5. Trainer registration, onboarding, activation, and supply readiness come first
6. Owner waitlist is passive only
7. `/ops` is Normal Ops, not an admin dashboard
8. No unrestricted admin CRUD
9. No routine manual matching
10. No routine manual billing
11. `Database = truth`
12. `/ops = readable operating view`
13. `audit_log = decision trail`
14. `CSV/export = proof only`

## Global site contract

Every public-facing page must satisfy these rules:
1. Shared header and footer
2. Clear primary action consistent with page intent
3. Mobile and desktop readable layout
4. Legal links available where appropriate
5. No dead buttons or dead links
6. No public copy that implies broad live matching is currently available
7. No UI that implies unrestricted admin, manual matching, or manual routine billing

## Route map

### Public website routes

Required public routes:
1. `/`
2. `/how-it-works`
3. `/about`
4. `/pricing`
5. `/trust`
6. `/faq`
7. `/contact`
8. `/privacy`
9. `/terms`
10. `/trainers`
11. `/submit`
12. `/submit/status/:submissionId`
13. `/trainer/billing`
14. `/trainer/reactivate`
15. `/t/:id` as the canonical trainer-detail route
16. `/trainers/:id` as a compatibility alias to the trainer-detail route
17. `/lp/:campaign`
18. `/melbourne/:suburb`
19. `/follow-up/:token`

### Protected oversight route

Required protected oversight route:
1. `/ops`

### Route intent rules

1. The home entry must remain waitlist-first while `PUBLIC_MATCHING_ENABLED=false`.
2. Trainer onboarding must remain visible and usable during the supply-first phase.
3. Trainer detail and connect flows may exist as lifecycle surfaces without being the primary home-entry path.
4. Follow-up, billing, reactivation, and submission-status routes are lifecycle routes, not broad public-marketing entry points.
5. `/ops` is a passcode-gated oversight route, not a public user-marketing route.

## Page specifications

### `/`

Purpose:
1. Public knowledge hub
2. Passive owner waitlist entry
3. Trainer-acquisition signpost

Required sections:
1. Hero/value proposition
2. Clear current public posture summary
3. Practical owner guidance or education blocks
4. Passive owner waitlist form
5. Strong trainer onboarding CTA
6. Supporting CTAs to `how-it-works`, `faq`, and `contact`

Required behavior:
1. Home must not expose broad public live matching while `PUBLIC_MATCHING_ENABLED=false`.
2. Waitlist capture must preserve suburb and consent.
3. Trainer onboarding CTA must remain obvious.
4. Copy must reinforce supply-first posture and passive owner demand.
5. Future matching-mode home behavior is outside the current 30-day supply-first prelaunch scope and must not be implied while `PUBLIC_MATCHING_ENABLED=false`.

### `/how-it-works`

Purpose:
1. Explain what DTD does
2. Explain the current supply-first posture
3. Explain how owners and trainers interact with the site now

Required sections:
1. DTD explanation
2. Supply-first explanation
3. Owner waitlist explanation
4. Trainer onboarding explanation
5. Consent/trust explanation

### `/about`

Purpose:
1. Explain the product and its intent
2. Position DTD as a guided match-and-intro platform, not a generic directory

Required sections:
1. Product framing
2. Why supply quality matters
3. Bounded oversight / automation-first model

### `/pricing`

Purpose:
1. Explain trainer-side commercial model
2. Avoid misleading owner-facing marketplace language

Required sections:
1. Intro-first billing explanation
2. Trial-free or billing-readiness explanation where applicable
3. Clear non-guarantee wording

### `/trust`

Purpose:
1. Explain trust, consent, and operating boundaries

Required sections:
1. Consent and contact-release explanation
2. Verification / quality framing
3. Oversight and accountability framing

### `/faq`

Purpose:
1. Answer owner and trainer questions without implying broad public live matching

Required sections:
1. Owner waitlist answers
2. Trainer onboarding answers
3. Billing/remediation answers
4. Support path

### `/contact`

Purpose:
1. Canonical support/contact path

Required sections:
1. Contact method
2. Expected use cases
3. Canonical mailbox `info@dogtrainersdirectory.com.au`

### `/privacy` and `/terms`

Purpose:
1. Provide legal and consent baseline

Required sections:
1. Current legal copy
2. Contact/support details where relevant

### `/trainers`

Purpose:
1. Trainer acquisition and qualification entry

Required sections:
1. Trainer value proposition
2. How intros work
3. Submission path
4. Next-step expectations

Required controls:
1. Primary CTA to `/submit`
2. Support path

### `/submit`

Purpose:
1. Trainer submission and activation start

Required sections:
1. Trainer details form
2. Consent and billing terms
3. Submission result and next-step state

### `/submit/status/:submissionId`

Purpose:
1. Explain trainer submission and activation state

Required sections:
1. Current status
2. Blockers
3. Next-step guidance
4. CTAs into billing/remediation/reactivation paths where relevant

### `/trainer/billing`

Purpose:
1. Trainer billing remediation

Required sections:
1. Billing profile summary
2. Current issue or blocker summary
3. Recovery or reconnect actions
4. Support path

### `/trainer/reactivate`

Purpose:
1. Trainer reactivation path

Required sections:
1. Reactivation context
2. Recovery checklist
3. Support path

### `/t/:id` and `/trainers/:id`

Purpose:
1. Trainer detail and contact-release lifecycle surface

Route rule:
1. `/t/:id` is the canonical public trainer-detail route
2. `/trainers/:id` is an alias to the same lifecycle surface

Required sections:
1. Trainer profile summary
2. Connect form
3. Contact-reveal result
4. Follow-up expectation

Required behavior:
1. Consent is required before contact release
2. Successful connect reveals contact information
3. Contact actions are trackable as engagement signals

### `/lp/:campaign` and `/melbourne/:suburb`

Purpose:
1. Campaign and SEO landing entry
2. Route traffic into the approved current home-entry path

Required sections:
1. Intent-specific message
2. Single strong CTA back into the approved owner or trainer path

Required behavior:
1. These pages must not imply broad public live matching is currently active
2. Attribution context must be preserved into downstream flows

### `/follow-up/:token`

Purpose:
1. Outcome confirmation and follow-up lifecycle surface

Required sections:
1. Intro/trainer context
2. Outcome action choices
3. Confirmation state

### `/ops`

Purpose:
1. Readable operating view for Normal Ops

Scope rule:
1. This page spec defines the intended `/ops` surface and boundaries.
2. It does not claim that every intended section is already implemented in the current runtime.

Required sections:
1. Auth gate
2. Current launch posture and public exposure summary
3. Supply-readiness summary
4. Trainer submissions, intro-ready supply, and blocked supply visibility
5. Readiness recommendation and blockers to next phase
6. Loop health and alert visibility
7. Revenue and billing visibility
8. Waitlist, growth, source-ingestion, and reactivation visibility
9. Recent system-action visibility

Required controls:
1. Login submit
2. Refresh
3. Sign out

Forbidden controls:
1. No unrestricted admin CRUD
2. No public-matching enable toggle in Normal Ops
3. No launch-phase mutation control in Normal Ops
4. No routine manual matching controls
5. No routine manual billing controls

## Completeness rule

The intended website is page-complete only when:
1. all listed routes exist
2. each route matches its purpose and required sections
3. copy and CTA structure match the locked website posture
4. `/ops` remains a readable operating view, not an admin control room
5. no page contradicts the supply-first launch posture or the locked operating rules
