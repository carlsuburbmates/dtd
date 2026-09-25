#!/usr/bin/env bash
set -euo pipefail

# Script to deploy backend API to Google Cloud Run in staging sandbox (dogtrainersdirectory-dev)
# Usage:
#   bash scripts/deploy_sandbox.sh

PROJECT_ID="dogtrainersdirectory-dev"
REGION="australia-southeast1"
SERVICE_NAME="dtd-api-dev"
SERVICE_ACCOUNT="625222421634-compute@developer.gserviceaccount.com"

validate_health_response() {
  HEALTH_RESPONSE="$1" python3 - <<'PY'
import json
import os

try:
    health = json.loads(os.environ["HEALTH_RESPONSE"])
except (KeyError, json.JSONDecodeError) as error:
    raise SystemExit(f"Sandbox health response was not valid JSON: {error}")

if health.get("ok") is not True or health.get("database") != "available":
    raise SystemExit("Sandbox health response did not confirm an available database")
PY
}

main() {
if [ "$#" -ne 0 ]; then
  echo "Usage: bash scripts/deploy_sandbox.sh" >&2
  exit 64
fi

# 1. Run the mandatory local preflight suite.
echo "🔍 [1/3] Running preflight code compilation and tests..."
python3 -m py_compile backend/server.py backend/worker.py backend/services/*.py
node scripts/check_prelaunch_release_gate.js
if [ -x ".venv/bin/python" ]; then
  .venv/bin/python backend/scripts/run_isolated_integration_suite.py
fi
echo "✅ Preflight tests passed!"

# 2. Deploy to Google Cloud Run
echo "🚀 [2/3] Deploying ${SERVICE_NAME} to Google Cloud Run in project ${PROJECT_ID} (${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --source backend \
  --allow-unauthenticated \
  --service-account "${SERVICE_ACCOUNT}" \
  --set-env-vars DB_NAME=dtd_sandbox,SENTRY_ENVIRONMENT=staging,DISABLE_AUTONOMY=1,ENABLE_STARTUP_SEEDS=0,ACTIVE_REGION="Greater Melbourne",ACTIVE_REGIONS="Greater Melbourne",AUTONOMY_LOOP_OWNER=none,PUBLIC_LAUNCH_PHASE=live_matching,PUBLIC_MATCHING_ENABLED=1,PUBLIC_MONETIZATION_COPY_MODE=flat_subscription,PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY=1,PUBLIC_SHOW_FOUNDING_PROFILE_COPY=0,RESEND_FROM="no-reply@dogtrainersdirectory.com.au",RESEND_REPLY_TO="info@dogtrainersdirectory.com.au",CORS_ORIGINS="*",PRO_TRIAL_DAYS=30,PRO_TRIAL_EXPIRY_WARNING_DAY=23,SPONSOR_MAX_SUBURBS_PER_TRAINER=4,SEO_MIN_PUBLISHED_TRAINERS=3,SEO_MIN_CONTENT_WORDS=500 \
  --set-secrets MONGO_URL=dtd-mongo-url:latest,ADMIN_PASS=dtd-admin-pass:latest,TRAINER_ACTION_TOKEN_SECRET=dtd-trainer-action-token-secret:latest,STRIPE_SECRET_KEY=dtd-stripe-secret-key:latest,STRIPE_WEBHOOK_SECRET=dtd-stripe-webhook-secret:latest,RESEND_API_KEY=dtd-resend-api-key:latest,ABR_GUID=dtd-abr-guid:latest,SENTRY_DSN=dtd-sentry-dsn:latest \
  --cpu 1 \
  --memory 1Gi \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 2

# 3. Post-deployment verification
echo "📡 [3/3] Verifying deployed endpoint..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="value(status.url)")
if [ -z "${SERVICE_URL}" ]; then
  echo "Sandbox Cloud Run service returned no URL" >&2
  exit 1
fi
echo "Sandbox URL: ${SERVICE_URL}"

HEALTH_RESPONSE=$(curl --fail --silent --show-error --location --max-time 15 "${SERVICE_URL}/api/health")
validate_health_response "${HEALTH_RESPONSE}"
echo "✅ Sandbox health verified: API is healthy and its database is available."

echo "🎉 Sandbox deployment and verification complete!"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
