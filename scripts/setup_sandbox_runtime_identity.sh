#!/usr/bin/env bash
set -euo pipefail

# Provision the dedicated, least-privilege Cloud Run identity used only by the
# developer sandbox. This script is idempotent and does not change production.
# Usage:
#   bash scripts/setup_sandbox_runtime_identity.sh

PROJECT_ID="dogtrainersdirectory-dev"
SERVICE_ACCOUNT_NAME="dtd-api-dev-runtime"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

ensure_project_role() {
  local role="$1"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${role}" \
    --condition=None >/dev/null
}

main() {
  if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
      --project="${PROJECT_ID}" \
      --display-name="DTD developer sandbox Cloud Run runtime"
  fi

  # Vertex is required only for the bounded matching adapter. The Cloud Run
  # service agent, not this runtime identity, manages container execution.
  ensure_project_role "roles/aiplatform.user"
  ensure_project_role "roles/secretmanager.secretAccessor"

  echo "Sandbox runtime identity ready: ${SERVICE_ACCOUNT}"
  echo "Next: bash scripts/deploy_sandbox.sh"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
