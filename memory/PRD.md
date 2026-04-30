# Bark&Bond — Pay-on-Outcome Dog-Training Match Engine

## Original problem statement (iter 2)
Build an autonomous business operating system. **Pick the optimal model, not preserve the directory.** Maximise revenue → automation → simplicity, in that order.

## Strategic decision (iter 2)
The product is now a **match engine**, not a directory. Visibility is bought only through outcomes. Revenue is performance-only.

## Architecture
- **Backend** (FastAPI + Motor + MongoDB):
  - `services/engine.py` — four background loops (ranking, pricing, verification, health) scheduled at startup.
  - `services/ai.py` — Claude Sonnet 4.5 for verification, matching, SEO copy.
  - `server.py` — primary product surface (`/api/match`, `/api/intros`, `/api/conversions`, `/api/submissions`, `/api/seo/{slug:path}`) and a single read-only `/api/oversight`. NO admin mutation endpoints.
- **Frontend** (React + Tailwind + shadcn):
  - `/` — single input → 3 ranked match cards inline.
  - `/t/:id` — Connect form → reveal contact + bill intro fee → "I hired them" → bill conversion.
  - `/submit` — auto-publish flow (no human gate).
  - `/trainers` — info page for trainers (no browse list).
  - `/melbourne/:suburb` — auto-generated SEO landing.
  - `/ops` — passcode-gated read-only oversight surface.

## Monetisation (iter 2)
- **Per-intro fee** ~A$3–A$8, dynamically priced per suburb by demand multiplier.
- **Conversion tracking** at launch (confirmations are tracked outcomes, not billed by default).
- **No subscriptions, no tiers, no featured upsells.**

## Autonomous loops
| Loop | Cadence | Effect |
|---|---|---|
| Ranking | 60 s | Bayesian outcome score (Beta posterior over conversion-from-intro) per trainer |
| Pricing | 90 s | Per-(suburb) intro fee from rolling 7-day demand; clipped 0.6× – 2.5× |
| Verification | 6 h | Re-score listings; auto-publish ≥0.85, auto-hide <0.6 |
| Health | 45 s | Anomaly snapshot + alerts; populates `system_state.health` |

## Implemented (2026-04-25, iter 2)
- All four loops live; first pass runs at startup so the very first request has pricing + outcome scores.
- Submissions are decided by the system: ≥0.85 auto-published verified, 0.6–0.84 auto-published unverified, <0.6 auto-held.
- Read-only oversight at `/ops` surfaces revenue, throughput, alerts, loop status, dynamic pricing per suburb, top trainers by outcome score, audit log, submissions auto-handled. No mutating buttons.
- Legacy routes (`/admin`, `/admin/dashboard`, `/match`, `/pricing`) redirect to current surfaces.
- 32/32 backend pytest cases pass; full frontend flow tested.

## Personas
1. **Dog owner** — types problem → gets 3 trainers → clicks Connect → contacts them.
2. **Trainer** — submits self via `/submit`; auto-published if evidence checks out; pays only when matched + hired.
3. **Operator** — reads `/ops`; pushes nothing.

## Backlog
- P1: Stripe integration to replace `billing_status="billed"` with real PaymentIntents; same on conversions endpoint.
- P1: Conversion email outreach (T+7d) so users get prompted to confirm hiring.
- P2: Real autonomous ingestion worker (scheduled scrape of public sources).
- P2: Bayesian early-stopping experiment engine running header-copy / match-count variants.
- P2: Anomaly auto-rollback (last-known-good config snapshots).
- P3: Trainer self-serve outcome dashboard (read-only; how they're trending).
- P3: Conversation IP fraud-scoring on `/api/conversions` for parity with `/api/intros`.

## Next tasks (suggested)
1. Keep launch in intro-first mode (`track_only` conversions), then enable conversion bill mode when fraud and signal quality are stable.
2. Outbound email for hire-confirmation (Resend).
3. Spin up the autonomous ingestion worker.
