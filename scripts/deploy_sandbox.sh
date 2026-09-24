#!/usr/bin/env bash
set -euo pipefail

# Script to deploy backend API to Google Cloud Run in staging sandbox (dogtrainersdirectory-dev)
# Usage:
#   bash scripts/deploy_sandbox.sh [--skip-tests]

PROJECT_ID="dogtrainersdirectory-dev"
REGION="australia-southeast1"
SERVICE_NAME="dtd-api-dev"
SERVICE_ACCOUNT="625222421634-compute@developer.gserviceaccount.com"

# 1. Run local test suite unless skipped
SKIP_TESTS=0
for arg in "$@"; do
  if [ "$arg" == "--skip-tests" ]; then
    SKIP_TESTS=1
  fi
done

if [ "$SKIP_TESTS" -eq 0 ]; then
  echo "🔍 [1/3] Running preflight code compilation and tests..."
  python3 -m py_compile backend/server.py backend/worker.py backend/services/*.py
  node scripts/check_prelaunch_release_gate.js
  if [ -x ".venv/bin/python" ]; then
    .venv/bin/python backend/scripts/run_isolated_integration_suite.py
  fi
  echo "✅ Preflight tests passed!"
else
  echo "⚠️ Skipping preflight tests per --skip-tests flag"
fi

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
echo "Sandbox URL: ${SERVICE_URL}"

HEALTH_STATUS=$(curl -sSL --max-time 15 "${SERVICE_URL}/api/health" || true)
echo "Health Response: ${HEALTH_STATUS}"

echo "🎉 Sandbox deployment and verification complete!"
