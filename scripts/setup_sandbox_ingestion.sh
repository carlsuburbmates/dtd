#!/usr/bin/env bash
set -euo pipefail

# Script to provision Vertex AI IAM permissions, APIs, and Cloud Scheduler for DTD sandbox ingestion
# Project: dogtrainersdirectory-dev
# Usage:
#   bash scripts/setup_sandbox_ingestion.sh

PROJECT_ID="dogtrainersdirectory-dev"
REGION="australia-southeast1"
SERVICE_ACCOUNT="625222421634-compute@developer.gserviceaccount.com"
SERVICE_NAME="dtd-api-dev"
SCHEDULER_JOB_NAME="dtd-trainer-ingest-cron"

main() {
  echo "🚀 [1/3] Enabling Vertex AI API in ${PROJECT_ID}..."
  gcloud services enable aiplatform.googleapis.com --project="${PROJECT_ID}"
  echo "✅ Vertex AI API enabled."

  echo "🔐 [2/3] Granting Vertex AI User (roles/aiplatform.user) to ${SERVICE_ACCOUNT}..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --condition=None
  echo "✅ Vertex AI User IAM role bound."

  echo "⏰ [3/3] Provisioning Cloud Scheduler job for batch ingestion..."
  SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="value(status.url)" || true)
  if [ -z "${SERVICE_URL}" ]; then
    echo "⚠️ Warning: Sandbox Cloud Run service ${SERVICE_NAME} returned no URL. Cloud Scheduler will need to be configured after deployment." >&2
    return 0
  fi

  JOB_URI="${SERVICE_URL}/api/internal/jobs/trainer-ingest"

  # Check if scheduler job exists; create or update idempotently
  if gcloud scheduler jobs describe "${SCHEDULER_JOB_NAME}" --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
    echo "Updating existing Cloud Scheduler job ${SCHEDULER_JOB_NAME}..."
    gcloud scheduler jobs update http "${SCHEDULER_JOB_NAME}" \
      --project="${PROJECT_ID}" \
      --location="${REGION}" \
      --schedule="0 2 * * *" \
      --time-zone="Australia/Melbourne" \
      --uri="${JOB_URI}" \
      --http-method=POST \
      --oidc-service-account-email="${SERVICE_ACCOUNT}" \
      --oidc-token-audience="${SERVICE_URL}"
  else
    echo "Creating Cloud Scheduler job ${SCHEDULER_JOB_NAME}..."
    gcloud scheduler jobs create http "${SCHEDULER_JOB_NAME}" \
      --project="${PROJECT_ID}" \
      --location="${REGION}" \
      --schedule="0 2 * * *" \
      --time-zone="Australia/Melbourne" \
      --uri="${JOB_URI}" \
      --http-method=POST \
      --oidc-service-account-email="${SERVICE_ACCOUNT}" \
      --oidc-token-audience="${SERVICE_URL}"
  fi
  echo "✅ Cloud Scheduler job ${SCHEDULER_JOB_NAME} successfully configured."
  echo "🎉 Ingestion pipeline infrastructure setup complete!"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
