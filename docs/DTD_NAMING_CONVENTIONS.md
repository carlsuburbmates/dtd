# DTD Naming Conventions and Cloud Resource Identity

**Reconciled:** 13 November 2026 — owner accepted Option A (IDs immutable, display names uniform).
**Scope:** main Dog Trainers Directory repository. This document is the single canonical map from role names to cloud identifiers, so no other document, script or platform has to guess which project is which.

## Why this document exists

The production project carries an auto-generated ID, `gen-lang-client-0028123502`. It is not discoverable by searching for `dogtrainersdirectory`, `dogtrainersdirectory-prod` or `dtd-prod`, and it was repeatedly mistaken for an unrelated AI Studio project. That ambiguity is the reason this record exists.

## Canonical map

| Role | Project ID (immutable) | Display name | Cloud Run | Runtime identity | Database |
| --- | --- | --- | --- | --- | --- |
| Developer sandbox | `dogtrainersdirectory-dev` | `dogtrainersdirectory-dev` | `dtd-api-dev`, `dtd-web-dev` | `dtd-api-dev-runtime@`, `dtd-web-dev-runtime@` | Atlas `dtd_sandbox` |
| Production | `gen-lang-client-0028123502` | `dogtrainersdirectory-prod` | `dtd-api` | `dtd-runtime@` | Atlas `DTD` |

Other identifiers that are **not** DTD environments and must not be used for DTD work:

| Project ID | Display name | Note |
| --- | --- | --- |
| `cs-host-60fd0869cbb444919338a9` | Cloud Setup Host Project | hosting support project, no DTD workload |
| `rugged-layout-508517-n1` | My First Project | unrelated default project |
| `gen-lang-client-0708827466` | Default Gemini Project | unrelated AI Studio project |
| `gen-lang-client-0028123502` | **dogtrainersdirectory-prod** | this is DTD production — the ID looks unrelated but the role is not |
| `spring-nation-tv0qz`, `studio-4393409652-4c3c4` | — | other products, other account |

## Immutable identifiers — do not attempt to rename

- **GCP project IDs are immutable.** `gen-lang-client-0028123502` can never become `dogtrainersdirectory-prod`. Only the display name is mutable, and it was set on 13 November 2026.
- **Firebase Hosting site IDs are pinned to the project ID.** `.firebaserc` and `firebase.json` declare `"site": "gen-lang-client-0028123502"`. That value is load-bearing for the live domain and must not be edited.
- Cloud Run service names, service accounts, buckets and Container Registry paths that embed the project ID cannot be renamed in place either.

## Decision — Option A accepted (13 November 2026)

**Decision:** accept the immutable IDs; make only the mutable display name uniform.

**Rationale:** making the identifiers themselves uniform would require creating a new project and migrating Cloud Run, the Firebase Hosting site, the live domain mapping, service accounts, all Secret Manager values, the Atlas allowlist, Cloud Scheduler, monitoring and GitHub wiring. That is a migration with production downtime and full secret rotation, not a rename, and it delivers no functional benefit.

**Option B (not taken, recorded for completeness):** a future migration to a project IDed `dogtrainersdirectory-prod` would require, in order: create project and enable APIs; recreate Artifact Registry and runtime service accounts; deploy `dtd-api`; create a new Firebase Hosting site and re-point `dogtrainersdirectory.com.au` (DNS and certificate change, expected downtime); copy and rotate every Secret Manager value; update the Atlas network allowlist and database user; recreate Cloud Scheduler, alert policies and log configuration; update `.firebaserc`/`firebase.json`, the 29 functional references in this repository and any deployment wiring. Revisit only if a concrete requirement makes the ID itself significant.

## Rules for code, scripts and documents

1. **Functional configuration must use the literal project ID.** Deployment scripts, `.firebaserc`, `firebase.json`, tests, monitoring setup and gcloud commands keep the real ID. Rewriting those to a friendly name breaks them.
2. **Prose should use the role name**, not a bare ID: "developer sandbox" or "production". Where an ID is genuinely required for reproducibility, write both — for example `production (dogtrainersdirectory-prod, project ID gen-lang-client-0028123502)`.
3. **Never infer the environment from the project ID alone.** The production ID is `gen-lang-client-0028123502`; use this map.
4. **Do not add new resources with environment-specific names that contradict this map.** New Cloud Run services in the sandbox take the `-dev` suffix; production services take no suffix.

## Where the identifiers appear

| Location | Count | Action |
| --- | --- | --- |
| Repository references to the production ID | 29 files | keep literal (rule 1) |
| Repository references to the sandbox ID | 40 files | keep literal (rule 1) |
| `.firebaserc` | 1 | keep literal — load-bearing |
| `firebase.json` hosting site | 1 | keep literal — load-bearing |
| GitHub repository secrets and variables | 0 | none required |
| gcloud configurations | 1 (`default`) | active project is the sandbox |

## Verification

```sh
gcloud projects describe dogtrainersdirectory-dev      --format="value(projectId,name)"
gcloud projects describe gen-lang-client-0028123502    --format="value(projectId,name)"
# expect: dogtrainersdirectory-dev / dogtrainersdirectory-dev
#         gen-lang-client-0028123502 / dogtrainersdirectory-prod
```

To revert the display name:

```sh
gcloud projects update gen-lang-client-0028123502 --name="dogtrainersdirectory"
```
