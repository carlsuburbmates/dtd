#!/usr/bin/env bash
set -euo pipefail

# Secrets exist only in this child process. The Python runner never prints them.
PROJECT_ID="dogtrainersdirectory-dev"
export MONGO_URL="$(gcloud secrets versions access latest --project="${PROJECT_ID}" --secret=dtd-mongo-url)"
export ADMIN_PASS="$(gcloud secrets versions access latest --project="${PROJECT_ID}" --secret=dtd-admin-pass)"
trap 'unset MONGO_URL ADMIN_PASS' EXIT

PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi
"${PYTHON_BIN}" scripts/run_sandbox_matching_matrix.py --execute "$@"
