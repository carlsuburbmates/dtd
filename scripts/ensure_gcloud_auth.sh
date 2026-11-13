#!/usr/bin/env bash
set -euo pipefail

# Keep human management credentials in the user's normal gcloud credential
# store. This helper only refreshes the existing account when a scoped read
# proves that saved credentials need reauthentication.
readonly EXPECTED_ACCOUNT="admin@dogtrainersdirectory.com.au"
readonly PROJECT_ID="dogtrainersdirectory-dev"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "Google Cloud CLI (gcloud) is not installed or is not on PATH." >&2
  exit 127
fi

active_account="$(gcloud config get-value account 2>/dev/null || true)"
if [[ "${active_account}" != "${EXPECTED_ACCOUNT}" ]]; then
  echo "Selecting the existing DTD management account in the gcloud CLI."
  gcloud auth login "${EXPECTED_ACCOUNT}"
fi

probe_output=""
if ! probe_output="$(gcloud projects describe "${PROJECT_ID}" \
  --account="${EXPECTED_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --format='value(projectId)' 2>&1)"; then
  if ! grep -Eqi 'Reauthentication failed|ReauthFailError|invalid_grant|reauthentication required' \
    <<<"${probe_output}"; then
    echo "The scoped Google Cloud read failed for a reason other than expired authentication; no login was started." >&2
    exit 1
  fi
  echo "Saved gcloud credentials need renewal; starting the official sign-in flow."
  # Without --force, gcloud reuses valid stored credentials and only opens the
  # browser flow when a fresh credential is needed.
  gcloud auth login "${EXPECTED_ACCOUNT}"
fi

active_account="$(gcloud config get-value account 2>/dev/null || true)"
if [[ "${active_account}" != "${EXPECTED_ACCOUNT}" ]]; then
  echo "gcloud did not activate the expected DTD management account." >&2
  exit 1
fi

verified_project="$(gcloud projects describe "${PROJECT_ID}" \
  --account="${EXPECTED_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --format='value(projectId)')"
if [[ "${verified_project}" != "${PROJECT_ID}" ]]; then
  echo "The scoped Google Cloud project read did not verify the DTD sandbox." >&2
  exit 1
fi

echo "Google Cloud CLI access verified: ${EXPECTED_ACCOUNT} on ${PROJECT_ID}."
