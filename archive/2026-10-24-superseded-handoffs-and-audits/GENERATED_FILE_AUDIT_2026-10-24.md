# Generated local-file audit — 24 October 2026

## Scope and disposition

Audited ignored/generated files in the main DTD checkout at `389130e` and classified current local outputs in the isolated audit checkout at `89daf56`. This is a local filesystem operation, separate from runtime release acceptance and the documentation relocation. No source, provider state, database or Git history was deleted or changed by the artifact moves.

**Completed:** 26 selected roots, **2,252 files and links / 430,185,250 bytes**, moved to a private local archive outside the Git checkout. All 2,248 regular-file hashes and four symlink targets were verified before and after moving, then independently rechecked. Original selected paths are absent. Permanent deletions: **zero**. The same-disk archive preserves restoration and does not reclaim disk space.

## Decisions and evidence

| Artifact group | Decision | Evidence / reason |
|---|---|---|
| Legacy `frontend/.next` (224 files; 389 MB) | Archive | Output dates to 29 April; current scripts and Dockerfile build/serve Vite `build/`; no active tracked reference or open handle. |
| `.venv_h04` (1,744 files/links; 25.3 MB) | Archive intact | Older isolated Python3.14.3 installation, no active tracked reference or open handle. Preserve all symlinks; restore to its original path before activation. Current `.venv` stays available. |
| Root/frontend Vercel metadata (4 files) | Archive | Retired local delivery metadata; current Cloud Run/Firebase workflow retained. No remote Vercel operation. |
| Six 11 October matching screenshots | Archive privately | `verify_matching_visuals.py` produces mocked visual fixtures, creates its output directory and can regenerate them. Preserve these as dated visual records; they do not establish current runtime acceptance. |
| Three security-handoff/patch exports and one nine-document review ZIP | Archive privately | Both patch boundary commits are in current ancestry; `.txt`/`.patch` hashes match. Preserve both and the dated ZIP as historical artifacts without publishing raw contents. |
| September provider debug log | Archive privately | Dated diagnostics, no active reference/open handle; current Hosting deployment cache retained. Log contents are not included in this public record. |
| Python bytecode, pytest caches and four active-tree Finder metadata files (269 items) | Archive | Producers are identifiable and outputs are regenerable. Tracked source/fixtures retained; no active open handle. |
| Current `.venv` and `frontend/node_modules` | Retain | Current workflows and isolated checkout symlinks use them; dependencies are not obsolete output. |
| Current Vite build and Hosting cache | Retain | Current build/deployment verification consumes them. Their presence does not prove a deployed release. |
| Local configuration/access notes, skill lock metadata, registered worktrees and existing archive content | Retain | Intentional/private configuration or resumable project work; not generated clutter. Configuration values and historical archive contents were not inspected for this decision. |
| 115 current isolated-checkout artifacts/links | Retain with recorded reason | Current candidate build, current cleanup manifests/verification, regenerable caches for the active checkpoint and shared dependency links. |

All 64,386 originally enumerated ignored entries in the main checkout have an archival or retention decision: 2,252 archived and 62,134 retained. Producer/dependency/reference classification is scoped; this is not a content/security audit of every installed dependency or private configuration file. There are no unexplained artifact entries in this inventory.

## Manifest, restoration and verification

The private archive contains `manifest.json` with original/destination paths, classifications, reasons, per-file SHA-256 or symlink target and completed verification; `retained-inventory.json` and `isolated-retained-inventory.json` explain retained outputs. Its owner-only archive root is outside this public repository. Raw payloads are intentionally not committed.

Restore only a selected root after checking its manifest and confirming the original path is absent. Rename it back to that exact original path; never overwrite newly generated output. The local archive README records this restoration procedure. No permanent-deletion authorization follows from an archive manifest.

Post-checks: all 26 selected source paths absent; 2,252 archived entries match manifests; 11 required active dependency/build/cache/configuration paths remain available; main checkout tracked Git status remains clean. No tests run: producer/reference, open-handle, byte-integrity, dependency-availability and Git checks cover this file-management scope.
