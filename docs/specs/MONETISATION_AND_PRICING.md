# Monetisation and Pricing

## Principles

- Dog owners use DTD free of charge.
- DTD takes no commission and charges no per-lead or per-introduction fee.
- Trainer products use flat, transparent prices. Statutory Australian Consumer Law rights are not limited by this specification.

## Product matrix

| Product | Price | Core entitlement | Inventory |
| --- | ---: | --- | --- |
| Free/Core | A$0 | Claim/manage an eligible listing and receive direct enquiries | Not scarce |
| Pro | A$19/month or A$149/year | Enhanced profile and Pro visibility features | Not suburb inventory |
| Suburb Sponsorship | A$39/month | Sponsored visibility for one named suburb | Two active businesses per suburb; four suburbs per business by default |
| Melbourne-Wide | A$199/month | Citywide sponsored visibility | Five active positions |

There is no A$99 Regional Sponsor tier. Legacy strings do not create a product.

## Pro trial

1. The trial is available only for eligible first-time Pro subscriptions.
2. Cohort admission requires Stripe live mode and a valid `STRIPE_LIVE_ANCHOR_AT`.
3. A trainer's qualifying registration/claim timestamp must be at or after that anchor.
4. Stripe subscription creation starts the 30-day provider-backed trial.
5. Persist provider trial dates and consumption state. A trainer cannot consume another trial.
6. The day-23 warning is sent once through the normal notification/audit path.
7. Test-mode records and pre-anchor registrations do not silently enter the live cohort.

## Sponsorship inventory

- Reservations are time-limited and idempotent.
- Inventory becomes reusable after expiry, cancellation or refund.
- A business cannot occupy the same suburb twice.
- The canonical business-wide suburb cap is four. Configuration remains safety-clamped between three and five; changing the policy value requires a decision-register update.
- Billing success activates reserved inventory; failure or timeout must release or surface the reservation for intervention.
- `past_due` is surfaced to `/ops` while Stripe's collection process remains open. Terminal `unpaid` and `incomplete_expired` states remove paid entitlement; a sponsor reservation is then released. A future grace-period policy requires a decision-register amendment and an end-to-end implementation.

## Refunds and cancellation

- Monthly-plan refund window: 14 days from the first billing cycle. This includes Pro monthly, Suburb Sponsorship and Melbourne-Wide.
- Annual Pro refund window: 30 days.
- Eligibility is not the same as execution. Production refunds remain fail-closed until live payments, authenticated operator action, confirmation, idempotency, Stripe result persistence, inventory release and audit evidence are verified.
- Trainer self-service portal/cancellation and operator refund are separate workflows. Public copy must describe only the workflow actually available.
- A configured Stripe key is not a commercial launch. New checkout is fail-closed unless `ENABLE_TRAINER_BILLING_CHECKOUT=1` is deliberately set at the final approved billing release.
- Checkout requires an active, versioned acceptance of the public trainer subscription terms. The accepted version and timestamp are persisted with the trainer billing profile.

## Acceptance evidence

For any commercial release, verify pricing UI → checkout API → Stripe object → webhook persistence → entitlement/inventory → notification/fallback → `/ops` evidence. A test checkout or configured secret alone is not acceptance.
