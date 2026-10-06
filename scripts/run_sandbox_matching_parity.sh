#!/usr/bin/env bash
set -euo pipefail

# The runner makes a short-lived, explicit developer-sandbox Cloud Run setting
# change and restores it itself.  It never targets the active gcloud default
# project; every provider request is explicitly scoped inside the Python runner.
PROJECT_ID="dogtrainersdirectory-dev"
EXPECTED_ACCOUNT="admin@dogtrainersdirectory.com.au"
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
if [ "${ACTIVE_ACCOUNT}" != "${EXPECTED_ACCOUNT}" ]; then
  echo "Refusing sandbox parity run: active gcloud account must be ${EXPECTED_ACCOUNT}." >&2
  exit 1
fi

export MONGO_URL="$(gcloud secrets versions access latest --project="${PROJECT_ID}" --secret=dtd-mongo-url)"
export ADMIN_PASS="$(gcloud secrets versions access latest --project="${PROJECT_ID}" --secret=dtd-admin-pass)"
trap 'unset MONGO_URL ADMIN_PASS' EXIT

PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi
"${PYTHON_BIN}" scripts/run_sandbox_matching_parity.py --execute "$@"
