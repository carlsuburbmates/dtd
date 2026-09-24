# DTD Targeted Post-Launch State

**Purpose:** the concrete next product and operating state.
**Status:** approved direction; individual implementation work still requires normal execution and release evidence.

## Target outcome

DTD should operate as a trustworthy Greater Melbourne directory that one non-technical founder can run through exceptions rather than constant manual supervision. Public claims, data, pricing, automation and `/ops` must agree with what production actually does.

## Work required to reach that state

1. **Complete geographic production state.** Apply and verify the canonical 539-record catalogue in the production `suburbs` collection. Keep database-first reads and the versioned static fallback; surface source/version/count in operations evidence.
2. **Make automation operationally truthful.** Repair stale loops, failed notifications and reactivation delivery. Every automated flow must expose last success, failure, retry/fallback and operator action in `/ops`.
3. **Reconcile the action layer.** Implement only approved, auditable `/ops` actions with confirmation and idempotency, or remove claims that they exist. Refund execution stays disabled until the live billing gate passes.
4. **Clean launch supply.** Review placeholder, discovery-seed, aggregator-only and unstructured-provenance profiles. Publish, hold, correct or suppress each under the acquisition specification.
5. **Complete SEO foundations.** Serve genuine sitemap and robots resources; compute per-suburb listing/content/indexation state; exclude ineligible pages; record Search Console evidence where available.
6. **Launch billing as one controlled event.** Move Stripe to live mode, set `STRIPE_LIVE_ANCHOR_AT` at the same time, verify webhook and portal behavior, and enable refunds only after tested operator and audit paths are ready.
7. **Finish observability.** Initialise Sentry in the deployed API path, keep first-party attribution privacy-bounded, and add a low-maintenance reporting view only where it materially reduces operator work.
8. **Close acceptance across each flow.** Validate UI → API → persisted state → notification/fallback → `/ops`, including degraded provider and duplicate/idempotent paths.

## Already-aligned contracts to preserve

- Free owner use; no commissions, per-lead or introduction fees.
- A$0/A$19/A$39/A$199 product set, with Pro annual at A$149 and no A$99 Regional tier.
- Thirty-day Pro trial anchored to Stripe live mode plus the explicit cohort timestamp, with day-23 warning.
- Two suburb sponsors per suburb, four sponsored suburbs per business by default, and five Melbourne-Wide positions.
- Diagnostic fit independent of payment, with commercial priority only in the five-point comparable-fit band.
- Interval-based refunds that include Melbourne-Wide monthly subscriptions.
- Separate First Leash deployment and privacy-safe static handoff.
- Lawful, evidence-bearing acquisition with suppression and trainer correction/removal rights.

## Acceptance definition

The target is reached only when code, automated tests, production configuration, live behavior, persisted data and operator-visible evidence agree. A local implementation, a successful API response, or a document alone is insufficient.
