#!/usr/bin/env bash
set -euo pipefail

# Script to provision Vertex AI IAM permissions, APIs, and Cloud Scheduler for DTD sandbox ingestion
# Project: dogtrainersdirectory-dev
# Usage:
#   bash scripts/setup_sandbox_ingestion.sh

PROJECT_ID="dogtrainersdirectory-dev"
REGION="australia-southeast1"
# This identity must first be provisioned by setup_sandbox_runtime_identity.sh.
# Keep scheduler invocation and application runtime on the same narrowly scoped
# identity so the application can validate its OIDC audience deterministically.
SERVICE_ACCOUNT="dtd-api-dev-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
SERVICE_NAME="dtd-api-dev"
SCHEDULER_JOB_NAME="dtd-trainer-ingest-cron"
# Use the same canonical Cloud Run audience that the deployed service enforces.
# `status.url` can retain a legacy service URL after a service migration.
SERVICE_URL="https://${SERVICE_NAME}-625222421634.${REGION}.run.app"

main() {
  if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Missing required sandbox runtime identity ${SERVICE_ACCOUNT}. Run scripts/setup_sandbox_runtime_identity.sh first." >&2
    exit 1
  fi

  echo "🚀 [1/3] Enabling Vertex AI and Cloud Scheduler APIs in ${PROJECT_ID}..."
  gcloud services enable aiplatform.googleapis.com cloudscheduler.googleapis.com --project="${PROJECT_ID}"
  echo "✅ APIs enabled."

  echo "🔐 [2/3] Granting Vertex AI User (roles/aiplatform.user) to ${SERVICE_ACCOUNT}..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --condition=None
  echo "✅ Vertex AI User IAM role bound."

  echo "⏰ [3/3] Provisioning Cloud Scheduler job for batch ingestion..."
  if ! gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" >/dev/null 2>&1; then
    echo "⚠️ Warning: Sandbox Cloud Run service ${SERVICE_NAME} does not exist. Cloud Scheduler will need to be configured after deployment." >&2
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
      --update-headers="Content-Type=application/json" \
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
      --headers="Content-Type=application/json" \
      --oidc-service-account-email="${SERVICE_ACCOUNT}" \
      --oidc-token-audience="${SERVICE_URL}"
  fi
  echo "✅ Cloud Scheduler job ${SCHEDULER_JOB_NAME} successfully configured."
  echo "🎉 Ingestion pipeline infrastructure setup complete!"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
