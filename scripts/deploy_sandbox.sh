#!/usr/bin/env bash
set -euo pipefail

# Script to deploy backend API to Google Cloud Run in staging sandbox (dogtrainersdirectory-dev)
# Usage:
#   bash scripts/deploy_sandbox.sh

PROJECT_ID="dogtrainersdirectory-dev"
REGION="australia-southeast1"
SERVICE_NAME="dtd-api-dev"
# The runtime identity is deliberately separate from the project default
# Compute Engine service account. Provision it with
# `bash scripts/setup_sandbox_runtime_identity.sh` before deploying.
SERVICE_ACCOUNT="dtd-api-dev-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
# Cloud Run's regional service URL is stable for this sandbox service. It is
# also the exact OIDC audience configured on the scheduler job.
SERVICE_URL="https://${SERVICE_NAME}-625222421634.${REGION}.run.app"
PREFLIGHT_PYTHON="${DTD_PREFLIGHT_PYTHON:-.venv/bin/python}"

validate_preflight_interpreter() {
  if [ -n "${DTD_PREFLIGHT_PYTHON:-}" ] && [ ! -x "${PREFLIGHT_PYTHON}" ]; then
    echo "DTD_PREFLIGHT_PYTHON is not executable: ${PREFLIGHT_PYTHON}" >&2
    return 64
  fi
}

resolve_deploy_source_sha() {
  local repo_root="$1"
  local upload_files
  local untracked_upload_files
  local tracked_backend_files

  if ! git -C "${repo_root}" rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "Sandbox deployment requires a Git checkout with a committed source revision" >&2
    return 64
  fi
  if ! git -C "${repo_root}" diff --quiet HEAD -- backend; then
    echo "Sandbox deployment requires a clean committed backend source tree" >&2
    return 64
  fi
  if ! upload_files="$(gcloud meta list-files-for-upload "${repo_root}/backend")"; then
    echo "Could not determine the Cloud Run backend source upload set" >&2
    return 64
  fi
  if [ -z "${upload_files}" ]; then
    echo "Cloud Run backend source upload set is empty" >&2
    return 64
  fi
  validate_uploaded_backend_files "${repo_root}" "${upload_files}" || return $?
  git -C "${repo_root}" rev-parse HEAD
}

validate_uploaded_backend_files() {
  local repo_root="$1"
  local upload_files="$2"
  local tracked_backend_files
  local untracked_upload_files
  tracked_backend_files="$(git -C "${repo_root}" ls-files -- backend | sed 's#^backend/##' | sort)"
  untracked_upload_files="$(comm -23 <(printf '%s\n' "${upload_files}" | sort) <(printf '%s\n' "${tracked_backend_files}" | sort))"
  if [ -n "${untracked_upload_files}" ]; then
    echo "Sandbox source upload contains files that are not tracked by Git:" >&2
    printf '%s\n' "${untracked_upload_files}" >&2
    return 64
  fi
}

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

validate_deployed_traffic_response() {
  SERVICE_STATE="$1" python3 - <<'PY'
import json
import os

try:
    response = json.loads(os.environ["SERVICE_STATE"])
except (KeyError, json.JSONDecodeError) as error:
    raise SystemExit(f"Sandbox service state was not valid JSON: {error}")

state = response.get("status", response)
latest_created = state.get("latestCreatedRevisionName") or ""
latest_ready = state.get("latestReadyRevisionName") or ""
traffic = state.get("traffic") or []

if not latest_created:
    raise SystemExit("Sandbox service has no created revision")
if latest_ready != latest_created:
    raise SystemExit("Latest sandbox revision is not ready")
if not any(
    route.get("revisionName") == latest_created and int(route.get("percent") or 0) == 100
    for route in traffic
):
    raise SystemExit("Latest sandbox revision is not receiving 100 percent of traffic")
PY
}

main() {
if [ "$#" -ne 0 ]; then
  echo "Usage: bash scripts/deploy_sandbox.sh" >&2
  exit 64
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"
DEPLOY_SOURCE_SHA="$(resolve_deploy_source_sha "${REPO_ROOT}")"
REVISION_SUFFIX="r8-${DEPLOY_SOURCE_SHA:0:8}"
echo "Sandbox source revision: ${DEPLOY_SOURCE_SHA} (${REVISION_SUFFIX})"

# 1. Run the mandatory local preflight suite.
echo "🔍 [1/3] Running preflight code compilation and tests..."
validate_preflight_interpreter
python3 -m py_compile backend/server.py backend/worker.py backend/services/*.py
node scripts/check_prelaunch_release_gate.js
if [ -x "${PREFLIGHT_PYTHON}" ]; then
  "${PREFLIGHT_PYTHON}" backend/scripts/run_isolated_integration_suite.py
fi
echo "✅ Preflight tests passed!"

# 2. Deploy to Google Cloud Run
echo "🚀 [2/3] Deploying ${SERVICE_NAME} to Google Cloud Run in project ${PROJECT_ID} (${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --revision-suffix "${REVISION_SUFFIX}" \
  --source backend \
  --allow-unauthenticated \
  --service-account "${SERVICE_ACCOUNT}" \
  --set-env-vars DB_NAME=dtd_sandbox,SENTRY_ENVIRONMENT=staging,DISABLE_AUTONOMY=1,ENABLE_STARTUP_SEEDS=0,AUTONOMY_LOOP_OWNER=none,ENABLE_TRAINER_BILLING_CHECKOUT=0,OPS_SELF_HEALING_ENABLED=0,ACTIVE_REGION="Greater Melbourne",ACTIVE_REGIONS="Greater Melbourne",PUBLIC_LAUNCH_PHASE=live_matching,PUBLIC_MATCHING_ENABLED=1,PUBLIC_MONETIZATION_COPY_MODE=flat_subscription,PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY=1,PUBLIC_SHOW_FOUNDING_PROFILE_COPY=0,RESEND_FROM="no-reply@dogtrainersdirectory.com.au",RESEND_REPLY_TO="info@dogtrainersdirectory.com.au",CORS_ORIGINS="*",PRO_TRIAL_DAYS=30,PRO_TRIAL_EXPIRY_WARNING_DAY=23,SPONSOR_MAX_SUBURBS_PER_TRAINER=4,SEO_MIN_PUBLISHED_TRAINERS=3,SEO_MIN_CONTENT_WORDS=500,VERTEXAI_PROJECT=${PROJECT_ID},VERTEXAI_LOCATION=${REGION},GEMINI_MODEL=gemini-3.5-flash,CLOUD_SCHEDULER_OIDC_SERVICE_ACCOUNT=${SERVICE_ACCOUNT},CLOUD_SCHEDULER_OIDC_AUDIENCE=${SERVICE_URL} \
  --set-secrets MONGO_URL=dtd-mongo-url:latest,ADMIN_PASS=dtd-admin-pass:latest,TRAINER_ACTION_TOKEN_SECRET=dtd-trainer-action-token-secret:latest,STRIPE_SECRET_KEY=dtd-stripe-secret-key:latest,STRIPE_WEBHOOK_SECRET=dtd-stripe-webhook-secret:latest,RESEND_API_KEY=dtd-resend-api-key:latest,RESEND_WEBHOOK_SECRET=dtd-resend-webhook-secret:latest,ABR_GUID=dtd-abr-guid:latest,SENTRY_DSN=dtd-sentry-dsn:latest \
  --cpu 1 \
  --memory 1Gi \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 2

# 3. Post-deployment verification
echo "📡 [3/3] Verifying deployed endpoint..."
gcloud run services update-traffic "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --to-latest

SERVICE_STATE=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="json(status.latestCreatedRevisionName,status.latestReadyRevisionName,status.traffic)")
validate_deployed_traffic_response "${SERVICE_STATE}"
LATEST_CREATED_REVISION=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="value(status.latestCreatedRevisionName)")

DEPLOYED_SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="value(status.url)")
if [ -z "${DEPLOYED_SERVICE_URL}" ]; then
  echo "Sandbox Cloud Run service returned no URL" >&2
  exit 1
fi
echo "Sandbox URL: ${DEPLOYED_SERVICE_URL}"

HEALTH_RESPONSE=$(curl --fail --silent --show-error --location --max-time 15 "${DEPLOYED_SERVICE_URL}/api/health")
validate_health_response "${HEALTH_RESPONSE}"
echo "✅ Sandbox revision ${LATEST_CREATED_REVISION} serves 100% traffic; API health and database availability are verified."

echo "🎉 Sandbox API deployment and health verification complete."
echo "ℹ️ Scheduler and IAM bootstrap are intentionally separate: bash scripts/setup_sandbox_ingestion.sh"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
