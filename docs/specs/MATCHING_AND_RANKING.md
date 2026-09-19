# Matching and Ranking

## Objective

Return useful trainers based on owner needs and evidenced service suitability while keeping commercial influence bounded and explicit.

## Diagnostic fit

Current deterministic fit is:

```text
fit = (match_score × 0.70) + (outcome_score × 0.30) - policy_penalty
```

Paid tier, subscription state and billing fields do not enter this score. The AI matching prompt must likewise omit those fields.

## Comparable-fit tiebreak

1. Calculate all eligible trainers' fit scores.
2. Find the highest fit score.
3. A trainer is in the comparable-fit band only when the difference from the top is at most `0.05`.
4. Within that band, tier order is Melbourne-Wide (4), Suburb Sponsor (3), Pro (2), Claimed (1), base/unclaimed (0).
5. Outside the band, fit order is preserved; payment cannot lift a materially weaker match above a stronger one.
6. Deterministic stable fields resolve any remaining equality.

This replaces the former 15% “Pro Verification” fit weight.

## Directory browse ranking

General directory browsing is a visibility surface rather than a diagnostic recommendation. It may use suburb sponsorship, tier, verification, reviews and outcome evidence in the documented deterministic order. UI must not represent paid visibility as independent clinical suitability.

## Eligibility and safety

- Suppressed, delisted, unpublished, policy-ineligible or geographically ineligible trainers do not enter ranking.
- Missing evidence defaults conservatively; AI output does not override deterministic gates.
- Fallback radius/catchment expansion must remain visible to the user and must not invent local presence.

## Acceptance tests

- Changing paid tier alone never changes fit score.
- Tier can reorder two trainers inside the 0.05 band.
- Tier cannot promote a trainer outside the band above the best fit.
- Policy penalties and publication/suppression gates apply before commercial ordering.
- AI and deterministic fallback return compatible, explainable evidence fields.
