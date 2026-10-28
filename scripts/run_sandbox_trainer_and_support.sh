#!/usr/bin/env bash
set -euo pipefail

# Fetch sandbox-only secrets into this child process. Nothing prints a secret.
PROJECT_ID="dogtrainersdirectory-dev"
export MONGO_URL="$(gcloud secrets versions access latest --project="${PROJECT_ID}" --secret=dtd-mongo-url)"
export ADMIN_PASS="$(gcloud secrets versions access latest --project="${PROJECT_ID}" --secret=dtd-admin-pass)"
export DTD_SANDBOX_PROJECT_ID="${PROJECT_ID}"
trap 'unset MONGO_URL ADMIN_PASS DTD_SANDBOX_PROJECT_ID' EXIT

PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi
"${PYTHON_BIN}" scripts/verify_sandbox_trainer_and_support.py --execute "$@"
