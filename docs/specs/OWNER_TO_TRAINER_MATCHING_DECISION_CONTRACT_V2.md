# Owner-to-Trainer Matching Decision Contract v2

**Status:** implementation authority for the matching workstream. This defines the target behaviour; it does not claim that the currently deployed route implements it.

**Applies to:** owner questionnaire, triage, candidate eligibility, AI-assisted fit, deterministic fallback, presentation, enquiry handoff, records and matching operations.

**Non-goals:** clinical, veterinary, legal or behavioural-treatment advice; a guarantee of outcome or trainer availability; paid lead placement; using marketing copy, reviews, sponsorship or Maps/Places content as fit evidence.

## 1. Decision boundary

The matching decision has three non-interchangeable stages:

1. **Eligibility** — deterministic. May this trainer be considered for this request?
2. **Fit** — paid-neutral. How well do the permitted, structured facts suit this owner and dog?
3. **Presentation** — deterministic. How are suitable results displayed?

Commercial status is prohibited from eligibility and fit. It may order results only in the locked comparable-fit band described in section 6.

## 2. Owner request and privacy contract

`POST /api/match` accepts a versioned request. Unknown fields are ignored; all validated fields are bounded before storage or model use.

| Field | Rule |
| --- | --- |
| `suburb_or_postcode` | Required. Resolve against the canonical Greater Melbourne locality catalogue before querying. A postcode must resolve to one unambiguous in-scope locality or require a locality selection. Never interpolate it into a database regular expression. |
| `dog_age_months` | Required integer `0..360`. The service derives `puppy` `<6`, `adolescent` `6..18`, `adult` `19..83`, `senior` `84+`. |
| `primary_concerns` | Required, one or more canonical values: `basic_manners`, `pulling_leash`, `reactivity`, `aggression`, `separation_anxiety`, `barking`, `recall`, `socialisation`, `puppy_prep`, `other`, `unsure`. `other` or `unsure` requires a description. |
| `service_format` | Required: `in_home`, `facility_or_field`, `group_class`, `online_coaching`, or `any`. `any` is no format preference. |
| `method_preference` | Required explicit choice: `positive_reinforcement_only`, `balanced`, or `no_preference`. It is a compatibility boundary, not a quality score. |
| `behaviour_description` | Optional except for `other`/`unsure`; maximum 800 characters. Strip email addresses, phone numbers, addresses and URLs before model use. The original text is never put in a URL or analytics event. |
| `consent.match_processing` and `consent.terms` | Required before matching. `consent.referral_contact` is collected only before an enquiry; `consent.follow_up` is separately optional. |

The service stores the policy version, normalised selections, route, result IDs, consent timestamps, a short-lived opaque context token hash and sanitised reason codes. It does **not** persist the raw behaviour description in `match_events`. The browser keeps the opaque context token in `sessionStorage`, never in a query string. The server retains it for 30 days, after which the detailed record is deleted or irreversibly aggregated. Enquiry records retain only the minimum separately-consented context required by that workflow.

Initial protection baseline: apply an application-level, configuration-backed request limit of ten match attempts per IP-derived, non-reversible key in ten minutes, with a 30-second burst interval. The limiter must fail safely without storing a raw IP and must expose only aggregate/rate-limit reason codes to `/ops`.

## 3. Triage and owner-visible response states

Triage runs before ordinary eligibility. Deterministic red-flag detection has priority; Gemini may classify only among the same approved states and cannot generate freeform safety advice.

| State | Trigger | Owner response | Ordinary matching |
| --- | --- | --- | --- |
| `immediate_human_danger` | Clear current threat of serious harm, active attack, a child bite requiring immediate assistance, or an active court/police emergency. | Prominent, approved emergency card: if there is immediate danger call Triple Zero (000); link the current Victorian official source. Do not give handling or treatment instructions. | Stop. |
| `urgent_animal_health_support` | Possible acute animal-health need or uncertain urgent animal-health language. | Show a non-diagnostic disclaimer and only current official/provider-authored urgent-care records from the separate directory. If coverage is absent or stale, say so. | Stop unless the owner explicitly starts a later, non-urgent request. |
| `serious_behavioural_support` | Serious behavioural concern without the two emergency triggers. | Show approved support boundary and continue only with trainers whose verified capabilities satisfy normal eligibility. | Continue. |
| `needs_clarification` | Missing required structured data, contradictory selections/description, or an `other`/`unsure` concern without enough description. | Ask the smallest next question. Preserve non-sensitive entered selections in session only. | Do not score. |
| `recommendations` | At least one eligible candidate meets the defined fit evidence threshold. | Show one to three factual recommendation cards. | Continue. |
| `limited_local_results` | Fewer than three local eligible candidates; the disclosed expanded declared-service-area pool produced one or more suitable candidates. | Show actual local and expanded results, label expanded results, and explain that DTD looked beyond the selected locality. | Continue. |
| `no_confirmed_match` | No candidate has the required current capability evidence or no candidate meets fit evidence after the disclosed expansion. | A useful, transparent state: explain that DTD could not confirm a suitable match from current information; offer a filtered directory browse and optional coverage-interest path. Do not show a ranked card as a match. | Stop. |
| `degraded_recommendations` or `degraded_no_confirmed_match` | Gemini is unavailable, times out, rate-limits, or produces invalid output. | State that standard matching rules were used; render the deterministic outcome. | Deterministic only. |

`no_confirmed_match` is an evidence statement, not a blanket "do not manufacture a match" rule. It exists only where this contract's capability and fit conditions are not met. A useful shortlist is permitted whenever the conditions are met.

## 4. Eligibility (deterministic)

The input is `build_match_ready_projection()` plus trainer identity/contact facts, never raw trainer prose. A candidate must pass every applicable gate:

1. published, not suppressed, in active region, not subject to a revoked statutory status, and contact-ready;
2. current, permitted, validated match-ready projection facts with no invalidation;
3. a declared service-area match: exact canonical `serviced_suburbs` match, or declared `greater_melbourne` catchment. Distance/radius matching is prohibited until canonical coordinates and a separately verified geo policy exist;
4. explicit requested service-format support, unless `service_format` is `any`;
5. required concern/specialty mapping and life-stage support where those fields are relevant; missing support fails closed for that match path; and
6. explicit method compatibility where a preference was selected.

Run local eligibility first. If fewer than three candidates remain, run the expanded pool using only declared service areas/catchments. The response records `search_scope: local | expanded` and the locality is never represented as the location of an expanded result.

The canonical mapping between owner concerns, trainer specialties, formats and philosophy values is a versioned, tested table. Free text may help Gemini compare *already eligible* candidates; it may not create a mapping or relax a gate.

## 5. Fit (AI-assisted, deterministic fallback)

The eligible candidate pool is capped at 15. Gemini receives only the normalised owner selections, PII-sanitised optional description, decision-policy version and each candidate's permitted projected fields: ID, specialties, formats, life stages, philosophy, service-area facts and delivery constraints. It never receives commercial data, reviews, biographies, raw acquisition sources, Maps content, excluded candidates or the unsanitised original owner text.

Both Gemini and fallback return this schema:

```json
{
  "decision_state": "recommendations | limited_local_results | no_confirmed_match",
  "candidates": [{
    "trainer_id": "string",
    "match_score": 0.0,
    "reason_codes": ["capability_concern_match", "format_match"],
    "explanation": "Plain-language statement supported only by supplied facts."
  }],
  "reason_codes": ["string"],
  "degraded": false
}
```

Permitted card reason codes are `capability_concern_match`, `life_stage_match`, `format_match`, `method_preference_match`, `service_area_match`, `expanded_service_area`, and `serious_behavioural_support`. Explanations cite at least one matching fact and may not contain a diagnosis, outcome promise, superlative or unsupplied fact.

The deterministic fallback calculates coverage from the same mapping table and permits recommendations only where a candidate has at least one concern/capability match plus every selected hard compatibility condition. It assigns a repeatable paid-neutral score from concern coverage, life-stage, format, method and local/expanded service-area components. The initial qualification threshold is `0.60`, versioned as policy configuration and fixture-tested. No candidate receives the current unconditional `0.40` fallback baseline.

Gemini timeout is five seconds. A timeout, rate limit, unavailable provider or schema failure writes a sanitised degradation event and invokes fallback. A fixture passes parity only when the two paths have the same triage/decision state, the same deterministic eligible pool, compatible reason-code categories, factually true explanations, and the same qualified candidate set for unambiguous fixtures. Rank variation is allowed only among candidates whose final paid-neutral fit is within `0.05`.

## 6. Fit and presentation

Until outcome data has accepted attribution, sample sufficiency, freshness, appeal and anti-gaming rules, its component is exactly zero. The initial final-fit calculation is therefore:

```text
final_fit = match_score - policy_penalty
```

`policy_penalty` is allowed only for a documented non-commercial delivery limitation and is recorded with its reason. Contact readiness is an eligibility gate, not a hidden penalty. The former default `outcome_score = 0.05` must not influence matching.

After fit, select at most three candidates. Let `Smax` be the highest `final_fit`. Candidates where `Smax - final_fit <= 0.05` are in the comparable-fit band and may be ordered by the locked commercial tier order: `citywide` (4), `suburb_sponsor` (3), `pro` (2), `claimed` (1), `unclaimed` (0). Outside that band fit order is absolute. A stable non-commercial ID resolves any remaining tie. The API records raw fit and presentation order separately; public cards do not expose scores.

## 7. Enquiry, follow-up and operations

The trainer-profile handoff uses the opaque match context token. The profile may show factual match context but never the owner's original description. An enquiry requires separate referral/contact consent. Trainer notifications receive only the enquiry information the owner has chosen to release.

Follow-up is optional, idempotent and stateful: `pending`, `retryable_failure`, `delivered`, `suppressed`, `terminal_failure`. A failed follow-up has bounded backoff and a visible `/ops` recovery state; a successful delivery cannot be duplicated. Outcomes do not feed future fit until a later accepted policy version enables them.

`/ops` records and displays, without raw descriptions: policy version, route/state distribution, consent/retention status, search scope, eligible count, AI/fallback/degradation state, reason codes, presented IDs, capability freshness/invalidation, urgent-directory freshness/corrections and follow-up state. It has no manual matching or untracked override control.

## 8. Urgent-provider and Maps boundaries

The urgent-provider directory is a separate, official-source record type. Each entry requires provider category, official source URL, stated contact method, location/service area, stated hours, retrieval/verification date, freshness state and correction/removal path. It is not a trainer source and does not enter fit.

The only pre-populated human-emergency copy is the Victorian official Triple Zero (000) direction. The provider directory must not claim Melbourne-wide coverage until it has evidence for it. Before release, re-check the official Victorian emergency information, Veterinary Practitioners Registration Board sources and each provider's own contact/hours page.

Google Maps/Places remains disabled and separate. If later enabled, it must be user-initiated, attributed, session-bounded, excluded from DTD records, AI, eligibility and ranking, and reviewed against current Places data-storage and attribution rules before implementation.

## 9. Acceptance fixtures

The implementation must create fixtures for: local puppy manners; multi-concern in-home/method boundary; ambiguous input; thin local supply/expanded result; no current capability evidence; stale/suppressed projection; exact `0.05` band; outside-band paid candidate; each Gemini degradation route; immediate human danger; urgent animal-health support; serious behavioural support; trainer declaration gaming; privacy/URL leakage; follow-up retry; and `/ops` redaction. Every fixture names the expected decision state, eligible IDs, reason codes, disclosed search scope and AI/fallback parity rule.
