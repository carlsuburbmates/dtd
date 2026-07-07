# Canonical Integrations

Last updated: 2026-07-02

## 1. Purpose

This file is the single canonical inventory of external integrations used by
DTD.

Use it to:
1. identify every third-party platform the project actually connects to
2. locate the specific account, project, service, or file where possible
3. understand how integrations connect to each other
4. see what is directly verified versus only partially known
5. avoid relying on stale docs, memory, or scattered env references

This file does not store secrets. It records names, identifiers, endpoints,
file references, and verification results only.

## 2. Verification Standard

- `Confirmed`
  - directly supported by project evidence and verified through an accessible
    provider path, reachable hosted target, or concrete external identifier
- `Partial`
  - strong evidence exists, but full direct verification was not possible from
    the current session
- `Suspected`
  - referenced indirectly, but not strong enough to treat as active truth
- `Unresolved`
  - likely relevant, but currently lacks enough evidence or direct reach to
    classify safely

## 3. Integration Inventory

### GitHub

- Integration name: `GitHub`
- Category: Source control and deployment source
- Purpose in the project:
  - canonical code repository
  - upstream source for Vercel and Render deployments
- Where it is used:
  - git remote
  - Vercel deployment metadata
  - Render service repo linkage
- Evidence:
  - `git remote -v` -> `https://github.com/carlsuburbmates/dtd.git`
  - `git ls-remote https://github.com/carlsuburbmates/dtd.git HEAD` returned `d1d08ada3d5c60554a4f7a989de95a6392bd726f`
  - Vercel deployment metadata repeatedly identifies:
    - `githubCommitOrg=carlsuburbmates`
    - `githubCommitRepo=dtd`
    - `githubRepoId=1220905743`
  - GitHub connector account list returned installed account `carlsuburbmates`
- Verification method:
  - direct git remote reach
  - direct GitHub connector account read
  - cross-check against Vercel deployment metadata
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - `carlsuburbmates`
- Project / app / service / environment name if known:
  - repository `dtd`
- Access identifiers or access clues:
  - repo URL `https://github.com/carlsuburbmates/dtd.git`
  - repo id `1220905743`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://github.com/carlsuburbmates/dtd`
- Env vars or config keys that reference it:
  - none directly
- Notes / gaps / follow-up needed:
  - Vercel and Render both point back to this repo and the `main` branch

### Vercel

- Integration name: `Vercel`
- Category: Frontend hosting and deployment
- Purpose in the project:
  - hosts the frontend web application
  - serves the current safe hosted proof surface
- Where it is used:
  - `.vercel/project.json`
  - `frontend/.vercel/project.json`
  - `frontend/vercel.json`
  - hosted frontend aliases
  - deployment metadata linked to GitHub
- Evidence:
  - `.vercel/project.json` and `frontend/.vercel/project.json` both contain:
    - `projectId=prj_TviWWkrOzNENkY4cazM3XsRHyIR1`
    - `orgId=team_5Jzh8VcbTjO5MNniKHpivsCY`
    - `projectName=dtd`
  - Vercel project lookup confirmed:
    - project `dtd`
    - framework `create-react-app`
    - latest deployment `dpl_FuEr8Vdvsk5EAgYincQUVqeUx9Dd`
    - domains:
      - `dtd-ten.vercel.app`
      - `dtd-carlitos-projects-a62ff78f.vercel.app`
      - `dtd-git-main-carlitos-projects-a62ff78f.vercel.app`
  - Vercel project list confirmed a separate project also exists:
    - `dogtrainersdirectory`
    - id `prj_17gVuwxhwNCMjkcpNuWhQPsroubu`
  - direct hosted check:
    - `https://dtd-ten.vercel.app/` returned `200`
  - direct custom-domain check:
    - `https://dogtrainersdirectory.com.au` returned Vercel `DEPLOYMENT_NOT_FOUND`
    - `https://www.dogtrainersdirectory.com.au` returned Vercel `DEPLOYMENT_NOT_FOUND`
- Verification method:
  - direct Vercel project read
  - direct Vercel deployment read
  - direct hosted HTTP checks
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - confirmed account id `team_5Jzh8VcbTjO5MNniKHpivsCY`
  - team slug clue from Vercel inspector URLs: `carlitos-projects-a62ff78f`
- Project / app / service / environment name if known:
  - active project `dtd`
  - separate inventory/drift-risk project `dogtrainersdirectory`
  - latest production deployment `dpl_FuEr8Vdvsk5EAgYincQUVqeUx9Dd`
- Access identifiers or access clues:
  - project id `prj_TviWWkrOzNENkY4cazM3XsRHyIR1`
  - org id `team_5Jzh8VcbTjO5MNniKHpivsCY`
  - branch alias `dtd-git-main-carlitos-projects-a62ff78f.vercel.app`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://dtd-ten.vercel.app`
  - `https://dtd-carlitos-projects-a62ff78f.vercel.app`
  - `https://dtd-git-main-carlitos-projects-a62ff78f.vercel.app`
  - `https://dogtrainersdirectory.com.au`
  - `https://www.dogtrainersdirectory.com.au`
- Env vars or config keys that reference it:
  - no Vercel token or project key is referenced in committed code
- Notes / gaps / follow-up needed:
  - the actual public domains are not attached to the active confirmed Vercel
    project at the time of verification
  - the repo still contains a second Vercel project with the public-domain-style
    name, which remains drift risk

### Render

- Integration name: `Render`
- Category: Backend and worker hosting
- Purpose in the project:
  - hosts the API service and the background worker
- Where it is used:
  - `scripts/verify_stage_a_runtime.sh`
  - root `.env` `REMOTE_BACKEND_URL`
  - docs that reference `https://dtd-api.onrender.com`
- Evidence:
  - direct Render API verification returned two services:
    - `dtd-api`
    - `dtd-worker`
  - verified service details:
    - `dtd-api`
      - id `srv-d7plat9kh4rs73e92qcg`
      - type `web_service`
      - region `oregon`
      - runtime `docker`
      - health check path `/api/config`
      - url `https://dtd-api.onrender.com`
      - owner id `tea-d7p40r0g4nts73b6a7pg`
      - repo `https://github.com/carlsuburbmates/dtd`
      - branch `main`
      - suspended `suspended`
    - `dtd-worker`
      - id `srv-d7platpf9bms73alk5u0`
      - type `background_worker`
      - region `oregon`
      - runtime `docker`
      - owner id `tea-d7p40r0g4nts73b6a7pg`
      - repo `https://github.com/carlsuburbmates/dtd`
      - branch `main`
      - suspended `suspended`
  - direct backend check:
    - `https://dtd-api.onrender.com/api/config` returned `503`
    - response included `x-render-routing: suspend-by-user`
- Verification method:
  - repo verification script using current Render API credentials
  - direct hosted backend HTTP check
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - confirmed owner id `tea-d7p40r0g4nts73b6a7pg`
  - human-readable owner/team name not directly confirmed in-session
- Project / app / service / environment name if known:
  - services `dtd-api` and `dtd-worker`
- Access identifiers or access clues:
  - service ids:
    - `srv-d7plat9kh4rs73e92qcg`
    - `srv-d7platpf9bms73alk5u0`
  - dashboard URLs exist in Render API payloads
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://dtd-api.onrender.com`
  - `https://dtd-api.onrender.com/api/config`
- Env vars or config keys that reference it:
  - `RENDER_API_KEY`
  - `REMOTE_BACKEND_URL`
  - `REACT_APP_BACKEND_URL` currently points at the Render API in local
    frontend env
- Notes / gaps / follow-up needed:
  - both services are currently suspended
  - any integration depending on the live Render API is currently blocked until
    suspension is lifted

### MongoDB Atlas

- Integration name: `MongoDB Atlas`
- Category: Managed database
- Purpose in the project:
  - managed MongoDB cluster for application data
  - external verification target for runtime baseline
- Where it is used:
  - `MONGO_URL`
  - `scripts/verify_stage_a_runtime.sh`
  - backend runtime
- Evidence:
  - direct Atlas API verification confirmed project:
    - name `dtd`
    - id `69f240f59a5199065ed1fce0`
    - org id `69f240f59a5199065ed1fbcc`
  - direct Atlas cluster verification confirmed:
    - cluster name `DTD`
    - cluster id `69f241a5eec10d4c321bce41`
    - region `AP_SOUTHEAST_2`
    - backing provider `AWS`
    - instance size `M0`
    - state `IDLE`
    - SRV `mongodb+srv://dtd.e34l3on.mongodb.net`
  - direct Atlas database user verification confirmed:
    - username `dtd_app`
    - scope cluster `DTD`
  - direct access-list verification confirmed:
    - `0.0.0.0/0` rule present
    - one additional `/32` IP rule present
- Verification method:
  - repo verification script using current Atlas API credentials
  - direct Atlas group endpoint read
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - project `dtd`
  - org id `69f240f59a5199065ed1fbcc`
  - org display name not directly confirmed in-session
- Project / app / service / environment name if known:
  - Atlas project `dtd`
  - cluster `DTD`
- Access identifiers or access clues:
  - project id `69f240f59a5199065ed1fce0`
  - cluster id `69f241a5eec10d4c321bce41`
  - DB user `dtd_app`
  - SRV host `dtd.e34l3on.mongodb.net`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://cloud.mongodb.com/api/atlas/v2/groups/69f240f59a5199065ed1fce0`
  - `mongodb+srv://dtd.e34l3on.mongodb.net`
- Env vars or config keys that reference it:
  - `MONGO_URL`
  - `DB_NAME`
  - `MONGODB_ATLAS_PUBLIC_KEY`
  - `MONGODB_ATLAS_PRIVATE_KEY`
  - `MONGODB_ATLAS_PROJECT_ID`
  - local-only `MONGODB_ATLAS_PROJECT_NAME`
- Notes / gaps / follow-up needed:
  - Atlas user `dtd_app` currently has a role on database `barkbond`, while the
    active runtime DB name in env is `dtd`; this needs explicit confirmation as
    intentional or stale

### Stripe

- Integration name: `Stripe`
- Category: Payments and billing
- Purpose in the project:
  - creates and sends intro-fee invoices
  - receives invoice-related webhook events
- Where it is used:
  - `backend/services/stripe_billing.py`
  - backend env
  - docs and launch evidence references
- Evidence:
  - direct Stripe API account read confirmed:
    - account id `acct_1SYQKTEMxvH0GVI9`
    - business profile name `Dog Trainers Directory`
    - support email `info@dogtrainersdirectory.com.au`
    - business URL `dogtrainersdirectory.com.au`
    - default currency `aud`
    - `charges_enabled=true`
    - `payouts_enabled=true`
  - direct Stripe webhook read confirmed:
    - webhook id `we_1TSj7nEMxvH0GVI9DXZEAwPp`
    - status `enabled`
    - livemode `true`
    - url `https://dtd-api.onrender.com/api/stripe/webhook`
    - enabled events:
      - `invoice.finalized`
      - `invoice.sent`
      - `invoice.payment_failed`
      - `invoice.payment_succeeded`
      - `invoice.paid`
      - `invoice.voided`
      - `invoice.marked_uncollectible`
- Verification method:
  - direct Stripe API account read using current local secret
  - direct Stripe webhook endpoint list read
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - Stripe account for `Dog Trainers Directory`
- Project / app / service / environment name if known:
  - account id `acct_1SYQKTEMxvH0GVI9`
  - current webhook endpoint `we_1TSj7nEMxvH0GVI9DXZEAwPp`
- Access identifiers or access clues:
  - account id `acct_1SYQKTEMxvH0GVI9`
  - webhook id `we_1TSj7nEMxvH0GVI9DXZEAwPp`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://api.stripe.com/v1/account`
  - `https://api.stripe.com/v1/webhook_endpoints`
  - webhook target `https://dtd-api.onrender.com/api/stripe/webhook`
- Env vars or config keys that reference it:
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `STRIPE_DEFAULT_CURRENCY`
  - `STRIPE_INVOICE_DAYS_UNTIL_DUE`
  - `STRIPE_REQUIRE_BILLING_CONSENT`
- Notes / gaps / follow-up needed:
  - the confirmed webhook target currently points at the suspended Render API,
    so live event delivery will fail until Render is resumed

### Resend

- Integration name: `Resend`
- Category: Transactional email
- Purpose in the project:
  - send submission updates, trainer notifications, and automated outreach
- Where it is used:
  - `backend/services/notifications.py`
  - `backend/services/automation.py`
  - backend env and root verification env
- Evidence:
  - code directly posts to `https://api.resend.com/emails`
  - direct Resend API verification confirmed domain:
    - id `4357f81a-c6bd-4b1a-b4a7-70287d822f70`
    - domain `dogtrainersdirectory.com.au`
    - status `verified`
    - region `ap-northeast-1`
    - sending `enabled`
    - receiving `disabled`
  - current local backend runtime email values:
    - `RESEND_FROM=no-reply@dogtrainersdirectory.com.au`
    - `RESEND_REPLY_TO=info@dogtrainersdirectory.com.au`
  - current root verification env values:
    - `RESEND_FROM=onboarding@resend.dev`
    - `RESEND_REPLY_TO=info@dogtrainersdirectory.com.au`
- Verification method:
  - direct Resend domains API read
  - code inspection
  - local env comparison
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - not directly exposed by current session
- Project / app / service / environment name if known:
  - verified domain `dogtrainersdirectory.com.au`
- Access identifiers or access clues:
  - domain id `4357f81a-c6bd-4b1a-b4a7-70287d822f70`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://api.resend.com/emails`
  - `https://api.resend.com/domains`
  - sending domain `dogtrainersdirectory.com.au`
- Env vars or config keys that reference it:
  - `RESEND_API_KEY`
  - `RESEND_FROM`
  - `RESEND_REPLY_TO`
- Notes / gaps / follow-up needed:
  - backend runtime and root verification env currently disagree on the sender
    address; backend runtime uses the project domain, while root verification env
    still points at `onboarding@resend.dev`

### PostHog

- Integration name: `PostHog`
- Category: Product analytics and session recording
- Purpose in the project:
  - frontend analytics
  - session recording
- Where it is used:
  - `frontend/public/index.html`
  - deployed frontend HTML
- Evidence:
  - `frontend/public/index.html` contains:
    - `posthog.init("phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs", ...)`
    - `api_host: "https://us.i.posthog.com"`
  - direct hosted HTML fetch from `https://dtd-ten.vercel.app/` returned the
    same PostHog snippet and key
  - the committed runbook marks `REACT_APP_POSTHOG_*` as legacy non-required
    noise, which matches the current direct snippet approach
- Verification method:
  - code inspection
  - direct hosted HTML verification
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - not directly exposed by current session
- Project / app / service / environment name if known:
  - not directly exposed by current session
- Access identifiers or access clues:
  - public project key `phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://us.i.posthog.com`
  - asset loader pattern `https://us-assets.i.posthog.com/static/array.js`
- Env vars or config keys that reference it:
  - none in the active code path
  - legacy/noise references only:
    - `REACT_APP_POSTHOG_*`
    - `NEXT_PUBLIC_POSTHOG_*`
- Notes / gaps / follow-up needed:
  - project/workspace name could not be directly confirmed from current session

### Sentry

- Integration name: `Sentry`
- Category: Error monitoring and observability
- Purpose in the project:
  - worker/runtime error capture
  - org-level verification support
- Where it is used:
  - `backend/worker.py`
  - `backend/.env`
  - root `.env`
  - runbook verification guidance
- Evidence:
  - `backend/worker.py` initializes `sentry_sdk` when `SENTRY_DSN` is present
  - direct Sentry API verification confirmed organization:
    - name `DTD`
    - slug `dtd-i9`
    - id `4511302931709952`
  - direct org project list confirmed projects:
    - `barkbond-api`
      - id `4511305085222992`
      - environments `production`, `development`
    - `barkbond-web`
      - id `4511305085419600`
    - `javascript-nextjs`
      - id `4511302933545040`
  - local backend `SENTRY_DSN` parses to:
    - host `o4511302931709952.ingest.de.sentry.io`
    - project path `/4511305085222992`
  - this matches project id `4511305085222992` -> `barkbond-api`
- Verification method:
  - direct Sentry API organization/project reads
  - backend env DSN parsing without exposing the DSN secret material
  - code inspection
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - organization `DTD`
  - org slug `dtd-i9`
  - team `DTD`
- Project / app / service / environment name if known:
  - active DSN target appears to be `barkbond-api`
  - other visible projects:
    - `barkbond-web`
    - `javascript-nextjs`
  - local runtime env: `development`
- Access identifiers or access clues:
  - org id `4511302931709952`
  - team id `4511302931775568`
  - project ids:
    - `4511305085222992`
    - `4511305085419600`
    - `4511302933545040`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://sentry.io/api/0/organizations/dtd-i9/projects/`
  - ingest host `o4511302931709952.ingest.de.sentry.io`
- Env vars or config keys that reference it:
  - `SENTRY_DSN`
  - `SENTRY_ENVIRONMENT`
  - `SENTRY_TRACES_SAMPLE_RATE`
  - `SENTRY_ACCESS_TOKEN`
- Notes / gaps / follow-up needed:
  - current visible Sentry project naming still carries legacy `barkbond-*`
    names
  - the repo actively initializes Sentry in the worker path; current frontend
    Sentry wiring is not active in code

### Google Fonts

- Integration name: `Google Fonts`
- Category: Frontend asset delivery
- Purpose in the project:
  - serves the `Inter` font used by the frontend
- Where it is used:
  - `frontend/public/index.html`
  - deployed frontend HTML
- Evidence:
  - local HTML includes:
    - preconnect `https://fonts.googleapis.com`
    - preconnect `https://fonts.gstatic.com`
    - stylesheet `https://fonts.googleapis.com/css2?family=Inter:wght@600&display=swap`
  - direct hosted HTML fetch from `https://dtd-ten.vercel.app/` returned the
    same Google Fonts links
- Verification method:
  - code inspection
  - direct hosted HTML verification
- Verification status: `Confirmed`
- Account / workspace / org name if known:
  - none
- Project / app / service / environment name if known:
  - font family `Inter`
- Access identifiers or access clues:
  - stylesheet path `css2?family=Inter:wght@600&display=swap`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://fonts.googleapis.com`
  - `https://fonts.gstatic.com`
- Env vars or config keys that reference it:
  - none
- Notes / gaps / follow-up needed:
  - none beyond normal third-party font dependency considerations

### Figma

- Integration name: `Figma`
- Category: Design system and design review workspace
- Purpose in the project:
  - holds the design file referenced by the repo’s design sync docs
  - anchors the code-to-design token workflow
- Where it is used:
  - `docs/design/FIGMA_SYNC_PLAYBOOK.md`
  - `docs/design/FIGMA_COMPONENT_MAP.md`
  - `docs/design/README.md`
  - `frontend/design-tokens/dtd.figma.tokens.json`
- Evidence:
  - design sync playbook names target file:
    - URL `https://www.figma.com/design/Is3zJpOaGhUo2nrTFzHww6`
    - file key `Is3zJpOaGhUo2nrTFzHww6`
  - token file exists at:
    - `frontend/design-tokens/dtd.figma.tokens.json`
  - direct HTTP reach to the Figma file URL returned `403`, which confirms the
    path exists but requires a Figma-authenticated session
- Verification method:
  - repo doc and token-file inspection
  - direct HTTP reach test to the named file URL
- Verification status: `Partial`
- Account / workspace / org name if known:
  - not directly confirmed in-session
- Project / app / service / environment name if known:
  - Figma file key `Is3zJpOaGhUo2nrTFzHww6`
- Access identifiers or access clues:
  - file key `Is3zJpOaGhUo2nrTFzHww6`
- Related domains / endpoints / bucket names / webhook paths if known:
  - `https://www.figma.com/design/Is3zJpOaGhUo2nrTFzHww6`
- Env vars or config keys that reference it:
  - none
- Notes / gaps / follow-up needed:
  - current session did not have direct Figma-authenticated file metadata
  - this is a design-process integration, not a runtime integration

## 4. Integration Table

| Integration | Category | Purpose | Account / Workspace | Project / Service / Environment | Key Access Clues | Verification Status |
| --- | --- | --- | --- | --- | --- | --- |
| GitHub | Source control | Canonical repo and deploy source | `carlsuburbmates` | repo `dtd` | `https://github.com/carlsuburbmates/dtd.git`, repo id `1220905743` | Confirmed |
| Vercel | Frontend hosting | Hosts frontend and proof aliases | account id `team_5Jzh8VcbTjO5MNniKHpivsCY` | project `dtd`, project id `prj_TviWWkrOzNENkY4cazM3XsRHyIR1` | `dtd-ten.vercel.app`, latest deployment `dpl_FuEr8Vdvsk5EAgYincQUVqeUx9Dd`, separate project `dogtrainersdirectory` | Confirmed |
| Render | Backend hosting | Hosts API and worker | owner id `tea-d7p40r0g4nts73b6a7pg` | `dtd-api`, `dtd-worker` | service ids `srv-d7plat9kh4rs73e92qcg`, `srv-d7platpf9bms73alk5u0`, URL `https://dtd-api.onrender.com` | Confirmed |
| MongoDB Atlas | Managed database | Primary application database | project `dtd` | cluster `DTD` | project id `69f240f59a5199065ed1fce0`, SRV `dtd.e34l3on.mongodb.net`, DB user `dtd_app` | Confirmed |
| Stripe | Payments | Intro invoicing and webhook billing events | Stripe account for `Dog Trainers Directory` | account `acct_1SYQKTEMxvH0GVI9` | webhook `we_1TSj7nEMxvH0GVI9DXZEAwPp`, target `https://dtd-api.onrender.com/api/stripe/webhook` | Confirmed |
| Resend | Transactional email | Outbound notifications and outreach | not directly exposed | verified sending domain `dogtrainersdirectory.com.au` | domain id `4357f81a-c6bd-4b1a-b4a7-70287d822f70`, API `api.resend.com` | Confirmed |
| PostHog | Analytics | Frontend analytics and session recording | not directly exposed | project name not directly exposed | public key `phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs`, host `https://us.i.posthog.com` | Confirmed |
| Sentry | Monitoring | Worker/runtime error capture | org `DTD` (`dtd-i9`) | active DSN target appears `barkbond-api` | org id `4511302931709952`, project id `4511305085222992`, ingest host `o4511302931709952.ingest.de.sentry.io` | Confirmed |
| Google Fonts | Frontend asset | Delivers `Inter` font | none | `Inter` font family | `fonts.googleapis.com`, `fonts.gstatic.com` | Confirmed |
| Figma | Design workspace | Design sync and design review | not directly confirmed | file key `Is3zJpOaGhUo2nrTFzHww6` | `https://www.figma.com/design/Is3zJpOaGhUo2nrTFzHww6` | Partial |

## 5. Cross-Integration Notes

1. GitHub -> Vercel
   - Vercel deployment metadata confirms the frontend is deployed from the
     GitHub repo `carlsuburbmates/dtd` on branch `main`.

2. GitHub -> Render
   - Render services `dtd-api` and `dtd-worker` both point to the same GitHub
     repo and branch.

3. Vercel -> Render
   - `frontend/.env` currently points `REACT_APP_BACKEND_URL` at
     `https://dtd-api.onrender.com`.
   - At verification time, Vercel frontend aliases were reachable, but the
     Render backend was suspended and returned `503`.

4. Render -> Stripe
   - Stripe webhook delivery is configured to
     `https://dtd-api.onrender.com/api/stripe/webhook`.
   - Because the Render API service is currently suspended, Stripe webhook
     delivery is currently at risk or non-functional.

5. Render -> Resend
   - runtime notification flows use Resend from backend code running on Render.
   - If Render remains suspended, live transactional email flows cannot execute.

6. MongoDB Atlas -> Render
   - Render runtime depends on Atlas for database access.
   - Atlas is live and verified, but Render is suspended, so the external DB is
     ready while the compute layer is not.

7. Custom public domain split
   - `dogtrainersdirectory.com.au` is present in Stripe business profile and
     Resend verified domain state.
   - the same domain is not currently attached to the active Vercel project and
     returns `DEPLOYMENT_NOT_FOUND`.

8. Legacy naming drift
   - Sentry still exposes legacy `barkbond-*` project names.
   - Atlas DB role for `dtd_app` still targets database `barkbond`.
   - these do not automatically mean the integrations are unused, but they are
     strong drift signals.

## 6. Unresolved or Partial Items

1. Figma workspace/account identity
   - Evidence exists:
     - named file URL and key in the repo docs
     - token export file in the repo
     - direct URL path reachable but auth-protected
   - Still needs confirmation:
     - workspace/account name
     - direct file metadata from an authenticated Figma session

2. PostHog project/workspace identity
   - Evidence exists:
     - public key committed in frontend HTML
     - active analytics snippet present in hosted HTML
   - Still needs confirmation:
     - human-readable PostHog project name/id
     - workspace/org name

3. Support mailbox provider for `info@dogtrainersdirectory.com.au`
   - Evidence exists:
     - the address is used across product, Stripe, and Resend reply-to config
   - Still needs confirmation:
     - the actual mailbox provider or workspace hosting that inbox

4. Vercel custom-domain ownership and intended active project
   - Evidence exists:
     - active Vercel project `dtd`
     - separate Vercel project `dogtrainersdirectory`
     - public domains currently return `DEPLOYMENT_NOT_FOUND`
   - Still needs confirmation:
     - whether the public domains are intentionally detached
     - whether the separate `dogtrainersdirectory` project should be retained or removed

5. MongoDB Atlas database-name drift
   - Evidence exists:
     - env/runtime DB name is `dtd`
     - Atlas DB user `dtd_app` has role on database `barkbond`
   - Still needs confirmation:
     - whether this mismatch is harmless legacy state or a configuration bug

6. Sentry project scope drift
   - Evidence exists:
     - current DSN target maps to project `barkbond-api`
     - repo currently initializes Sentry in `backend/worker.py`
   - Still needs confirmation:
     - whether the current desired target should keep legacy BarkBond naming or
       be migrated/renamed

## 7. Maintenance Rule

When an integration is added, changed, suspended, migrated, or removed:
1. update this file in the same session as the integration change
2. verify the integration through the strongest available path before changing
   its status
3. never mark an entry `Confirmed` from code references alone when a stronger
   direct provider or hosted verification path is available
4. redact secrets and tokens; record only names, ids, domains, URLs, and safe
   access clues
5. if an older doc still owns overlapping integration inventory text, remove or
   reduce that overlap so this file remains the single canonical inventory
6. if runtime state changes materially, update:
   - this file
   - `docs/process/INTEGRATION_CREDENTIALS_RUNBOOK.md`
   - `docs/governance/EXECUTION_STATUS.md` if the integration change affects current execution truth
