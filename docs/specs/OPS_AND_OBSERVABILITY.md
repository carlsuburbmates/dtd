# Operations and Observability

## Operator model

DTD has one non-technical operator. `/ops` is the single action and evidence surface. It should prioritise exceptions, explain impact and provide the smallest safe next action.

## Required operating picture

- Public posture and commercial gates.
- Trainer acquisition, review, publication and suppression state.
- Enquiry/matching cases and follow-up state.
- Message delivery failures, retries and fallbacks.
- Billing, trial, webhook, refund and reactivation exceptions.
- Suburb and sponsor inventory source/capacity.
- Background-loop last success/failure and authenticated schedule evidence.
- Recent immutable audit events.

## Action contract

An action shown in `/ops` must exist end to end. Mutating actions require:

1. authenticated and authorised API boundary;
2. explicit target and confirmation for consequential changes;
3. idempotency or safe duplicate handling;
4. persisted before/after or provider result;
5. audit event with actor, reason and timestamp;
6. notification or fallback where the affected user needs one;
7. truthful success/failure feedback in `/ops`.

Old specifications that list approve/reject/merge/delist/cancel/refund as available do not make those controls real. Implement the approved bounded action or remove the claim.

## Automation contract

Each loop exposes owner, cadence/trigger, input cohort, last run, last success, failure count, next action and retry/fallback. A deployed function without scheduling evidence is not an active automation. Repeated failures become an operator case rather than disappearing into logs.

## Financial safety

- Stripe mutations fail closed when live mode, permission or feature gate is absent.
- Refund execution remains disabled until live-payment, operator-confirmation, idempotency, inventory-release and audit paths pass production acceptance.
- Trial day-23 warnings run once per eligible provider-backed trial and persist outcome evidence.

## Observability

- API health includes dependency status without exposing secrets.
- Sentry must initialise in the process actually serving production requests before being called active.
- PostHog remains privacy-bounded and is not operational authority.
- Add charts only where they reduce operator effort; a second operator system is not allowed.

## Operating cadence

- **Each session:** posture, failed/stale flows, work queue, message failures, billing/reactivation, inventory, recent changes.
- **Daily during launch:** resolve safety/identity/payment issues first; then delivery and supply exceptions.
- **Weekly:** review source health, catalogue/indexation drift, unresolved cases, provider costs and automation reliability.
- Refresh authenticated numbers before making an operational decision; never preserve a dated snapshot as live truth.
