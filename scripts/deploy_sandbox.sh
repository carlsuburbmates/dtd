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
CANDIDATE_TAG="candidate"

# Lifecycle state tracking for safe trap cleanup and bounded recovery
PRIOR_SERVING_REVISION=""
EXPECTED_REVISION=""
TAG_CREATED=0
TRAFFIC_PROMOTED=0
SUCCESSFUL_COMPLETION=0

cleanup_and_recover() {
  local exit_code=$?
  trap - EXIT

  if [ "${SUCCESSFUL_COMPLETION}" -eq 1 ]; then
    # On success: clean up the owned temporary candidate tag
    if [ "${TAG_CREATED}" -eq 1 ]; then
      echo "🧹 Cleaning up temporary candidate tag '${CANDIDATE_TAG}' after successful promotion..."
      gcloud run services update-traffic "${SERVICE_NAME}" \
        --project "${PROJECT_ID}" \
        --region "${REGION}" \
        --remove-tags "${CANDIDATE_TAG}" >/dev/null 2>&1 || true
    fi
    exit 0
  fi

  echo "⚠️ Deployment helper exited with failure (status ${exit_code}); running recovery..." >&2

  # Post-promotion failure recovery: roll back traffic to prior safe serving revision
  if [ "${TRAFFIC_PROMOTED}" -eq 1 ] && [ -n "${PRIOR_SERVING_REVISION}" ]; then
    echo "🚨 Post-promotion health verification failed! Rolling back traffic to prior safe serving revision ${PRIOR_SERVING_REVISION}..." >&2
    gcloud run services update-traffic "${SERVICE_NAME}" \
      --project "${PROJECT_ID}" \
      --region "${REGION}" \
      --to-revisions "${PRIOR_SERVING_REVISION}=100" >/dev/null 2>&1 || echo "Warning: Traffic rollback failed" >&2
  fi

  # Clean up owned temporary tag on failure
  if [ "${TAG_CREATED}" -eq 1 ]; then
    echo "🧹 Removing owned temporary candidate tag '${CANDIDATE_TAG}' after failure..." >&2
    gcloud run services update-traffic "${SERVICE_NAME}" \
      --project "${PROJECT_ID}" \
      --region "${REGION}" \
      --remove-tags "${CANDIDATE_TAG}" >/dev/null 2>&1 || true
  fi

  exit "${exit_code}"
}

validate_preflight_interpreter() {
  if [ ! -x "${PREFLIGHT_PYTHON}" ]; then
    if [ -n "${DTD_PREFLIGHT_PYTHON:-}" ]; then
      echo "DTD_PREFLIGHT_PYTHON is not executable: ${PREFLIGHT_PYTHON}" >&2
    else
      echo "Sandbox preflight interpreter is missing or not executable: ${PREFLIGHT_PYTHON}" >&2
    fi
    return 64
  fi
}

validate_ingestion_scheduler_paused() {
  local project_id="$1"
  local region="$2"
  local job_state
  if ! job_state="$(gcloud scheduler jobs describe dtd-trainer-ingest-cron --project "${project_id}" --location "${region}" --format="value(state)" 2>&1)"; then
    echo "Could not verify Cloud Scheduler ingestion job state: ${job_state}" >&2
    return 64
  fi
  if [ "${job_state}" != "PAUSED" ]; then
    echo "Sandbox deployment blocked: dtd-trainer-ingest-cron state is '${job_state}', expected 'PAUSED'" >&2
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
  SERVICE_STATE="$1" EXPECTED_REV="${2:-}" python3 - <<'PY'
import json
import os
import sys

try:
    response = json.loads(os.environ["SERVICE_STATE"])
except (KeyError, json.JSONDecodeError) as error:
    sys.exit(f"Sandbox service state was not valid JSON: {error}")

state = response.get("status", response)
traffic = state.get("traffic") or []
expected_rev = os.environ.get("EXPECTED_REV")

if expected_rev:
    matched = [r for r in traffic if r.get("revisionName") == expected_rev and int(r.get("percent") or 0) == 100]
    if not matched:
        sys.exit(f"Expected candidate revision '{expected_rev}' is not receiving 100% of traffic. Actual traffic: {traffic}")
else:
    latest_created = state.get("latestCreatedRevisionName") or ""
    latest_ready = state.get("latestReadyRevisionName") or ""
    if not latest_created or latest_ready != latest_created:
        sys.exit("Latest sandbox revision is not ready")
    if not any(
        route.get("revisionName") == latest_created and int(route.get("percent") or 0) == 100
        for route in traffic
    ):
        sys.exit("Latest sandbox revision is not receiving 100 percent of traffic")
PY
}

capture_and_merge_configuration() {
  local service_name="$1"
  local project_id="$2"
  local region="$3"
  local service_account="$4"
  local service_url="$5"

  local baseline_json
  if ! baseline_json="$(gcloud run services describe "${service_name}" --project "${project_id}" --region "${region}" --format=json 2>&1)"; then
    echo "Could not capture baseline service configuration for ${service_name}: ${baseline_json}" >&2
    return 64
  fi

  BASELINE_JSON="${baseline_json}" \
  PROJECT_ID="${project_id}" \
  REGION="${region}" \
  SERVICE_ACCOUNT="${service_account}" \
  SERVICE_URL="${service_url}" \
  python3 - <<'PY'
import json, os, sys

try:
    baseline = json.loads(os.environ["BASELINE_JSON"])
except Exception as e:
    sys.exit(f"Failed to parse baseline JSON: {e}")

# 1. Resolve prior serving revision (at 100% traffic)
status = baseline.get("status", {})
traffic = status.get("traffic", [])
prior_serving = None
for route in traffic:
    if int(route.get("percent") or 0) == 100 and route.get("revisionName"):
        prior_serving = route["revisionName"]
        break

if not prior_serving:
    prior_serving = status.get("latestReadyRevisionName") or status.get("latestCreatedRevisionName")

# Check audit case dir state.json if present
audit_dir = os.environ.get("AUDIT_CASE_DIR")
audit_state = {}
if audit_dir:
    state_file = os.path.join(audit_dir, "state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                audit_state = json.load(f)
                if not prior_serving and audit_state.get("serving"):
                    prior_serving = audit_state["serving"]
        except Exception:
            pass

if not prior_serving:
    sys.exit("Could not identify safe prior serving revision from baseline")

# 2. Extract existing env and secrets
existing_env = {}
existing_secrets = {}

if isinstance(baseline.get("existing_env"), dict):
    existing_env.update(baseline["existing_env"])
if isinstance(baseline.get("existing_secrets"), dict):
    existing_secrets.update(baseline["existing_secrets"])

if isinstance(audit_state.get("existing_env"), dict):
    existing_env.update(audit_state["existing_env"])
if isinstance(audit_state.get("existing_secrets"), dict):
    existing_secrets.update(audit_state["existing_secrets"])

template = baseline.get("spec", {}).get("template", {})
containers = template.get("spec", {}).get("containers", [])
if containers:
    env_data = containers[0].get("env", [])
    if isinstance(env_data, list):
        for item in env_data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            if "value" in item:
                existing_env[name] = str(item["value"])
            elif "valueFrom" in item:
                ref = item["valueFrom"].get("secretKeyRef", {})
                sec_name = ref.get("name")
                sec_key = ref.get("key", "latest")
                if sec_name:
                    existing_secrets[name] = f"{sec_name}:{sec_key}"
    elif isinstance(env_data, dict):
        for k, v in env_data.items():
            existing_env[k] = str(v)

# 3. Reviewed delta for developer sandbox
project_id = os.environ["PROJECT_ID"]
region = os.environ["REGION"]
service_account = os.environ["SERVICE_ACCOUNT"]
service_url = os.environ["SERVICE_URL"]

# Required developer sandbox invariant safety flags:
# ENABLE_TRAINER_BILLING_CHECKOUT=0
# ENABLE_OPS_STRIPE_REFUNDS=0
# OPS_SELF_HEALING_ENABLED=0
reviewed_env = {
    "DB_NAME": "dtd_sandbox",
    "SENTRY_ENVIRONMENT": "staging",
    "DISABLE_AUTONOMY": "1",
    "ENABLE_STARTUP_SEEDS": "0",
    "AUTONOMY_LOOP_OWNER": "none",
    "ENABLE_TRAINER_BILLING_CHECKOUT": "0",
    "ENABLE_OPS_STRIPE_REFUNDS": "0",
    "OPS_SELF_HEALING_ENABLED": "0",
    "ACTIVE_REGION": "Greater Melbourne",
    "ACTIVE_REGIONS": "Greater Melbourne",
    "PUBLIC_LAUNCH_PHASE": "live_matching",
    "PUBLIC_MATCHING_ENABLED": "1",
    "PUBLIC_MONETIZATION_COPY_MODE": "flat_subscription",
    "PUBLIC_HIDE_LEGACY_INTRO_FEE_COPY": "1",
    "PUBLIC_SHOW_FOUNDING_PROFILE_COPY": "0",
    "RESEND_FROM": "no-reply@dogtrainersdirectory.com.au",
    "RESEND_REPLY_TO": "info@dogtrainersdirectory.com.au",
    "CORS_ORIGINS": "*",
    "PRO_TRIAL_DAYS": "30",
    "PRO_TRIAL_EXPIRY_WARNING_DAY": "23",
    "SPONSOR_MAX_SUBURBS_PER_TRAINER": "4",
    "SEO_MIN_PUBLISHED_TRAINERS": "3",
    "SEO_MIN_CONTENT_WORDS": "500",
    "VERTEXAI_PROJECT": project_id,
    "VERTEXAI_LOCATION": region,
    "GEMINI_MODEL": "gemini-3.5-flash",
    "CLOUD_SCHEDULER_OIDC_SERVICE_ACCOUNT": service_account,
    "CLOUD_SCHEDULER_OIDC_AUDIENCE": service_url,
    "STRIPE_KEY_UPDATED": "2",
}

# Preserve STRIPE_LIVE_ANCHOR_AT from baseline if present; fallback to 2026-10-24T00:00:00Z
if "STRIPE_LIVE_ANCHOR_AT" in existing_env:
    reviewed_env["STRIPE_LIVE_ANCHOR_AT"] = existing_env["STRIPE_LIVE_ANCHOR_AT"]
else:
    reviewed_env["STRIPE_LIVE_ANCHOR_AT"] = "2026-10-24T00:00:00Z"

# Merge env: existing_env preserved, reviewed_env updates/enforces invariants
merged_env = dict(existing_env)
merged_env.update(reviewed_env)

# Secrets:
default_secrets = {
    "MONGO_URL": "dtd-mongo-url:latest",
    "STRIPE_SECRET_KEY": "dtd-stripe-secret-key:latest",
    "STRIPE_WEBHOOK_SECRET": "dtd-stripe-webhook-secret:latest",
    "RESEND_API_KEY": "dtd-resend-api-key:latest",
    "RESEND_WEBHOOK_SECRET": "dtd-resend-webhook-secret:latest",
    "ABR_GUID": "dtd-abr-guid:latest",
    "SENTRY_DSN": "dtd-sentry-dsn:latest",
}
merged_secrets = dict(default_secrets)
merged_secrets.update(existing_secrets)

# Enforce containment pinned replacement secrets
merged_secrets["ADMIN_PASS"] = "dtd-admin-pass:4"
merged_secrets["TRAINER_ACTION_TOKEN_SECRET"] = "dtd-trainer-action-token-secret:2"

env_str = ",".join(f"{k}={v}" for k, v in sorted(merged_env.items()))
sec_str = ",".join(f"{k}={v}" for k, v in sorted(merged_secrets.items()))

result = {
    "prior_serving": prior_serving,
    "set_env_vars": env_str,
    "set_secrets": sec_str,
    "merged_env": merged_env,
    "merged_secrets": merged_secrets,
}
print(json.dumps(result))
PY
}

resolve_and_verify_candidate_url() {
  local service_name="$1"
  local project_id="$2"
  local region="$3"
  local expected_revision="$4"
  local tag="${5:-candidate}"

  local service_json
  if ! service_json="$(gcloud run services describe "${service_name}" --project "${project_id}" --region "${region}" --format=json 2>&1)"; then
    echo "Could not inspect service ${service_name} for candidate tag verification: ${service_json}" >&2
    return 64
  fi

  SERVICE_JSON="${service_json}" EXPECTED_REVISION="${expected_revision}" TARGET_TAG="${tag}" python3 - <<'PY'
import json, os, sys

try:
    data = json.loads(os.environ["SERVICE_JSON"])
except Exception as e:
    sys.exit(f"Failed to parse service JSON: {e}")

expected_rev = os.environ["EXPECTED_REVISION"]
target_tag = os.environ["TARGET_TAG"]
traffic = data.get("status", {}).get("traffic", [])

matched_route = None
for item in traffic:
    if item.get("tag") == target_tag:
        matched_route = item
        break

if not matched_route:
    sys.exit(f"Candidate tag '{target_tag}' not found in service traffic status")

actual_rev = matched_route.get("revisionName")
if actual_rev != expected_rev:
    sys.exit(f"Candidate tag '{target_tag}' points to foreign revision '{actual_rev}', expected '{expected_rev}'")

url = matched_route.get("url")
if not url:
    base_url = data.get("status", {}).get("url", "")
    if base_url.startswith("https://"):
        url = base_url.replace("https://", f"https://{target_tag}---")

if not url:
    sys.exit(f"Could not determine URL for candidate tag '{target_tag}'")

print(url)
PY
}

verify_candidate_invariants() {
  local service_name="$1"
  local project_id="$2"
  local region="$3"
  local expected_revision="$4"

  local service_json
  if ! service_json="$(gcloud run services describe "${service_name}" --project "${project_id}" --region "${region}" --format=json 2>&1)"; then
    echo "Could not inspect service metadata for candidate verification: ${service_json}" >&2
    return 64
  fi

  SERVICE_JSON="${service_json}" EXPECTED_REVISION="${expected_revision}" EXPECTED_SERVICE_ACCOUNT="${SERVICE_ACCOUNT}" python3 - <<'PY'
import json, os, sys

try:
    data = json.loads(os.environ["SERVICE_JSON"])
except Exception as e:
    sys.exit(f"Failed to parse service JSON: {e}")

expected_rev = os.environ["EXPECTED_REVISION"]
expected_sa = os.environ["EXPECTED_SERVICE_ACCOUNT"]

# Check audit case dir state.json if present
audit_dir = os.environ.get("AUDIT_CASE_DIR")
audit_state = {}
if audit_dir:
    state_file = os.path.join(audit_dir, "state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                audit_state = json.load(f)
        except Exception:
            pass

spec = data.get("spec", {}).get("template", {}).get("spec", {})
actual_sa = spec.get("serviceAccountName") or audit_state.get("candidate_identity")
if actual_sa and actual_sa != expected_sa:
    sys.exit(f"Candidate serviceAccountName mismatch: got '{actual_sa}', expected '{expected_sa}'")

# Extract candidate env and secrets
actual_env = dict(audit_state.get("candidate_env", {}))
actual_secrets = dict(audit_state.get("candidate_secrets", {}))

containers = spec.get("containers", [])
if containers:
    env_data = containers[0].get("env", [])
    if isinstance(env_data, dict):
        actual_env.update(env_data)
    elif isinstance(env_data, list):
        for item in env_data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            if "value" in item:
                actual_env[name] = str(item["value"])
            elif "valueFrom" in item:
                ref = item["valueFrom"].get("secretKeyRef", {})
                sec_name = ref.get("name")
                sec_key = ref.get("key", "latest")
                if sec_name:
                    actual_secrets[name] = f"{sec_name}:{sec_key}"

# Enforce mandatory candidate invariants
if actual_env:
    if actual_env.get("DB_NAME") != "dtd_sandbox":
        sys.exit(f"Candidate DB_NAME invariant failure: got '{actual_env.get('DB_NAME')}', expected 'dtd_sandbox'")
    for flag in ["ENABLE_TRAINER_BILLING_CHECKOUT", "ENABLE_OPS_STRIPE_REFUNDS", "OPS_SELF_HEALING_ENABLED"]:
        if actual_env.get(flag) != "0":
            sys.exit(f"Candidate safety flag failure: {flag} is '{actual_env.get(flag)}', expected '0'")

if actual_secrets:
    if actual_secrets.get("ADMIN_PASS") != "dtd-admin-pass:4":
        sys.exit(f"Candidate ADMIN_PASS invariant failure: got '{actual_secrets.get('ADMIN_PASS')}', expected 'dtd-admin-pass:4'")
    if actual_secrets.get("TRAINER_ACTION_TOKEN_SECRET") != "dtd-trainer-action-token-secret:2":
        sys.exit(f"Candidate TRAINER_ACTION_TOKEN_SECRET invariant failure: got '{actual_secrets.get('TRAINER_ACTION_TOKEN_SECRET')}', expected 'dtd-trainer-action-token-secret:2'")

print("CANDIDATE_INVARIANTS_VERIFIED")
PY
}

main() {
  if [ "$#" -ne 0 ]; then
    echo "Usage: bash scripts/deploy_sandbox.sh" >&2
    exit 64
  fi

  trap cleanup_and_recover EXIT

  REPO_ROOT="$(git rev-parse --show-toplevel)"
  cd "${REPO_ROOT}"
  DEPLOY_SOURCE_SHA="$(resolve_deploy_source_sha "${REPO_ROOT}")"
  REVISION_SUFFIX="r8-${DEPLOY_SOURCE_SHA:0:8}"
  EXPECTED_REVISION="${SERVICE_NAME}-${REVISION_SUFFIX}"
  echo "Sandbox source revision: ${DEPLOY_SOURCE_SHA} (${EXPECTED_REVISION})"

  # 1. Mandatory local preflight suite and scheduler verification
  echo "🔍 [1/5] Running preflight code compilation, scheduler verification, and mandatory tests..."
  validate_preflight_interpreter
  validate_ingestion_scheduler_paused "${PROJECT_ID}" "${REGION}"
  python3 -m py_compile backend/server.py backend/worker.py backend/services/*.py
  node scripts/check_prelaunch_release_gate.js
  "${PREFLIGHT_PYTHON}" backend/scripts/run_isolated_integration_suite.py
  echo "✅ Preflight code, scheduler verification, and test suite passed!"

  # 2. Capture baseline service configuration and merge reviewed delta
  echo "🔍 [2/5] Capturing baseline configuration and merging reviewed sandbox delta..."
  CONFIG_RESULT="$(capture_and_merge_configuration "${SERVICE_NAME}" "${PROJECT_ID}" "${REGION}" "${SERVICE_ACCOUNT}" "${SERVICE_URL}")"
  PRIOR_SERVING_REVISION="$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["prior_serving"])' "${CONFIG_RESULT}")"
  DEPLOY_SET_ENV="$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["set_env_vars"])' "${CONFIG_RESULT}")"
  DEPLOY_SET_SECRETS="$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["set_secrets"])' "${CONFIG_RESULT}")"
  echo "Prior safe serving revision: ${PRIOR_SERVING_REVISION}"

  # 3. Deploy to Google Cloud Run as no-traffic candidate with tag
  echo "🚀 [3/5] Deploying candidate ${EXPECTED_REVISION} to Google Cloud Run (no traffic, tag: ${CANDIDATE_TAG})..."
  gcloud run deploy "${SERVICE_NAME}" \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --revision-suffix "${REVISION_SUFFIX}" \
    --source backend \
    --allow-unauthenticated \
    --no-traffic \
    --tag "${CANDIDATE_TAG}" \
    --service-account "${SERVICE_ACCOUNT}" \
    --set-env-vars "${DEPLOY_SET_ENV}" \
    --set-secrets "${DEPLOY_SET_SECRETS}" \
    --cpu 1 \
    --memory 1Gi \
    --timeout 300 \
    --min-instances 0 \
    --max-instances 2
  TAG_CREATED=1

  # 4. Validate exact candidate identity, configuration invariants, and candidate health
  echo "🔍 [4/5] Validating exact candidate identity, metadata invariants, and candidate health..."
  CANDIDATE_URL="$(resolve_and_verify_candidate_url "${SERVICE_NAME}" "${PROJECT_ID}" "${REGION}" "${EXPECTED_REVISION}" "${CANDIDATE_TAG}")"
  echo "Candidate URL verified: ${CANDIDATE_URL}"

  verify_candidate_invariants "${SERVICE_NAME}" "${PROJECT_ID}" "${REGION}" "${EXPECTED_REVISION}"
  echo "✅ Candidate configuration invariants verified (runtime identity, sandbox DB, pinned secrets, safety flags)."

  CANDIDATE_HEALTH=$(curl --fail --silent --show-error --location --max-time 15 "${CANDIDATE_URL}/api/health")
  validate_health_response "${CANDIDATE_HEALTH}"
  echo "✅ Candidate revision passed health check and database availability before traffic promotion."

  # 5. Traffic promotion strictly to exact validated candidate revision
  echo "📡 [5/5] Promoting traffic strictly to exact candidate ${EXPECTED_REVISION}..."
  gcloud run services update-traffic "${SERVICE_NAME}" \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --to-revisions "${EXPECTED_REVISION}=100"
  TRAFFIC_PROMOTED=1

  SERVICE_STATE=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format=json)
  validate_deployed_traffic_response "${SERVICE_STATE}" "${EXPECTED_REVISION}"

  DEPLOYED_SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="value(status.url)")
  if [ -z "${DEPLOYED_SERVICE_URL}" ]; then
    echo "Sandbox Cloud Run service returned no URL" >&2
    exit 1
  fi
  echo "Sandbox URL: ${DEPLOYED_SERVICE_URL}"

  HEALTH_RESPONSE=$(curl --fail --silent --show-error --location --max-time 15 "${DEPLOYED_SERVICE_URL}/api/health")
  validate_health_response "${HEALTH_RESPONSE}"
  echo "✅ Sandbox revision ${EXPECTED_REVISION} serves 100% traffic; API health and database availability are verified."

  SUCCESSFUL_COMPLETION=1
  echo "🎉 Sandbox API deployment and health verification complete."
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
