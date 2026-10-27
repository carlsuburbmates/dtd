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
PRIOR_SERVING_SAFE=0
EXPECTED_REVISION=""
TAG_CREATED=0
TRAFFIC_PROMOTED=0
SUCCESSFUL_COMPLETION=0
TAG_CLEANUP_FAILED=0

cleanup_and_recover() {
  local exit_code=$?
  trap - EXIT

  # 1. Post-promotion failure recovery: roll back traffic to prior safe serving revision
  if [ "${TRAFFIC_PROMOTED}" -eq 1 ] && [ "${SUCCESSFUL_COMPLETION}" -ne 1 ]; then
    if [ -n "${PRIOR_SERVING_REVISION}" ] && [ "${PRIOR_SERVING_SAFE}" -eq 1 ]; then
      local current_traffic_json
      current_traffic_json="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format=json 2>/dev/null || true)"
      local current_serving_now
      current_serving_now=$(CURRENT_JSON="${current_traffic_json}" python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ["CURRENT_JSON"])
    routes = data.get("status", {}).get("traffic", [])
    for r in routes:
        if int(r.get("percent") or 0) == 100 and r.get("revisionName"):
            print(r["revisionName"])
            sys.exit(0)
    print("")
except Exception:
    print("")
PY
      )
      if [ -n "${current_serving_now}" ] && [ "${current_serving_now}" != "${EXPECTED_REVISION}" ]; then
        echo "🚨 Intervening traffic change detected during recovery: current serving revision is '${current_serving_now}', not candidate '${EXPECTED_REVISION}'." >&2
        echo "Skipping automatic rollback to preserve concurrent operator's traffic. Guarded recovery required: current=${current_serving_now}, candidate=${EXPECTED_REVISION}, prior=${PRIOR_SERVING_REVISION}." >&2
      else
        echo "🚨 Post-promotion health verification failed! Rolling back traffic to prior safe serving revision ${PRIOR_SERVING_REVISION}..." >&2
        if ! gcloud run services update-traffic "${SERVICE_NAME}" \
          --project "${PROJECT_ID}" \
          --region "${REGION}" \
          --to-revisions "${PRIOR_SERVING_REVISION}=100"; then
          echo "Warning: Traffic rollback command failed" >&2
        fi
      fi
    else
      echo "🚨 Post-promotion failure occurred, but prior serving revision '${PRIOR_SERVING_REVISION}' is not verified safe (or no prior revision recorded)." >&2
      echo "Guarded recovery disposition: candidate revision '${EXPECTED_REVISION}' remains at 100% traffic until operator action. Unsafe rollback was prevented." >&2
    fi
  fi

  # 2. Clean up owned temporary candidate tag on both success and failure
  if [ "${TAG_CREATED}" -eq 1 ]; then
    local svc_tag_json
    svc_tag_json="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format=json 2>/dev/null || true)"
    local tag_owner
    tag_owner=$(SVC_JSON="${svc_tag_json}" TAG="${CANDIDATE_TAG}" python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ["SVC_JSON"])
    routes = data.get("status", {}).get("traffic", [])
    for r in routes:
        if r.get("tag") == os.environ["TAG"]:
            print(r.get("revisionName") or "")
            sys.exit(0)
    print("")
except Exception:
    print("")
PY
    )
    if [ -n "${tag_owner}" ]; then
      if [ -n "${EXPECTED_REVISION}" ] && [ "${tag_owner}" != "${EXPECTED_REVISION}" ]; then
        echo "Tag '${CANDIDATE_TAG}' is now mapped to revision '${tag_owner}', not candidate '${EXPECTED_REVISION}'. Skipping removal to preserve foreign tag." >&2
      else
        echo "🧹 Removing owned temporary candidate tag '${CANDIDATE_TAG}'..."
        if ! gcloud run services update-traffic "${SERVICE_NAME}" \
          --project "${PROJECT_ID}" \
          --region "${REGION}" \
          --remove-tags "${CANDIDATE_TAG}"; then
          echo "ERROR: Failed to remove temporary candidate tag '${CANDIDATE_TAG}'" >&2
          TAG_CLEANUP_FAILED=1
        fi
      fi
    fi
  fi

  if [ "${SUCCESSFUL_COMPLETION}" -eq 1 ]; then
    if [ "${TAG_CLEANUP_FAILED}" -eq 1 ]; then
      echo "Deployment succeeded but candidate tag cleanup failed." >&2
      exit 1
    fi
    exit 0
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

  if ! upload_files="$(gcloud meta list-files-for-upload backend 2>&1)"; then
    echo "Could not inspect Cloud Run upload candidate list for backend: ${upload_files}" >&2
    return 64
  fi

  if [ -z "${upload_files}" ]; then
    echo "Cloud Run backend upload candidate list is empty" >&2
    return 64
  fi

  if ! git -C "${repo_root}" diff --quiet -- backend; then
    echo "Sandbox deployment blocked: uncommitted changes detected under backend/" >&2
    return 64
  fi

  untracked_upload_files=()
  while IFS= read -r file; do
    [ -z "${file}" ] && continue
    if git -C "${repo_root}" check-ignore -q -- "backend/${file}"; then
      echo "Sandbox deployment blocked: upload includes ignored backend path 'backend/${file}'" >&2
      return 64
    fi
    if ! git -C "${repo_root}" ls-files --error-unmatch -- "backend/${file}" >/dev/null 2>&1; then
      untracked_upload_files+=("backend/${file}")
    fi
  done <<< "${upload_files}"

  if [ "${#untracked_upload_files[@]}" -gt 0 ]; then
    echo "Sandbox deployment blocked: untracked files would be uploaded from backend/:" >&2
    printf ' - %s\n' "${untracked_upload_files[@]}" >&2
    return 64
  fi

  tracked_backend_files="$(git -C "${repo_root}" ls-files backend)"
  while IFS= read -r file; do
    [ -z "${file}" ] && continue
    if ! grep -Fxq "${file#backend/}" <<< "${upload_files}"; then
      echo "Sandbox deployment blocked: tracked file '${file}' is omitted from upload candidates" >&2
      return 64
    fi
  done <<< "${tracked_backend_files}"

  git -C "${repo_root}" rev-parse HEAD
}

validate_health_response() {
  local response="$1"
  local ok
  local database

  if ! ok="$(python3 -c 'import json, sys; data = json.loads(sys.argv[1]); print(data.get("ok"))' "${response}" 2>/dev/null)"; then
    echo "Invalid JSON response from health endpoint: ${response}" >&2
    return 1
  fi

  database="$(python3 -c 'import json, sys; data = json.loads(sys.argv[1]); print(data.get("database"))' "${response}" 2>/dev/null || true)"

  if [ "${ok}" != "True" ] || [ "${database}" != "available" ]; then
    echo "Sandbox service failed health check: ${response}" >&2
    return 1
  fi
}

validate_deployed_traffic_response() {
  local response="$1"
  local expected_revision="${2:-}"

  RESPONSE_JSON="${response}" EXPECTED_REV="${expected_revision}" python3 - <<'PY'
import json, os, sys

try:
    data = json.loads(os.environ["RESPONSE_JSON"])
except Exception as e:
    sys.exit(f"Invalid JSON response from Cloud Run service describe: {e}")

status = data.get("status", {})
latest_created = status.get("latestCreatedRevisionName")
latest_ready = status.get("latestReadyRevisionName")
traffic = status.get("traffic", [])

if not latest_created or not latest_ready:
    sys.exit("Cloud Run service status is missing latest created or ready revision names")

if latest_created != latest_ready:
    sys.exit(
        f"Cloud Run service latest created revision '{latest_created}' does not match latest ready revision '{latest_ready}'"
    )

expected_rev = os.environ.get("EXPECTED_REV")
if expected_rev:
    if latest_created != expected_rev:
        sys.exit(f"Deployed revision mismatch: got '{latest_created}', expected '{expected_rev}'")

one_hundred_percent_revision = None
for route in traffic:
    if int(route.get("percent") or 0) == 100:
        one_hundred_percent_revision = route.get("revisionName")
        break

if not one_hundred_percent_revision:
    sys.exit("Cloud Run service does not route 100% traffic to any revision")

if one_hundred_percent_revision != latest_ready:
    sys.exit(
        f"Cloud Run 100% traffic route targets '{one_hundred_percent_revision}', expected latest ready revision '{latest_ready}'"
    )

if expected_rev and one_hundred_percent_revision != expected_rev:
    sys.exit(
        f"Cloud Run 100% traffic route targets '{one_hundred_percent_revision}', expected exact candidate '{expected_rev}'"
    )
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
    echo "Could not inspect service ${service_name} for baseline configuration: ${baseline_json}" >&2
    return 64
  fi

  local base_result
  if ! base_result=$(BASELINE_JSON="${baseline_json}" PROJECT_ID="${project_id}" REGION="${region}" SERVICE_ACCOUNT="${service_account}" SERVICE_URL="${service_url}" python3 - <<'PY'
import json, os, sys

try:
    baseline = json.loads(os.environ["BASELINE_JSON"])
except Exception as e:
    sys.exit(f"Failed to parse baseline JSON: {e}")

if not isinstance(baseline, dict) or not baseline:
    sys.exit("Baseline service metadata is empty or invalid")

# 1. Resolve prior serving revision (must be single 100% route)
status = baseline.get("status", {})
traffic = status.get("traffic", [])
prior_serving = None
non_zero_routes = [r for r in traffic if int(r.get("percent") or 0) > 0]

for route in non_zero_routes:
    if int(route.get("percent") or 0) == 100 and route.get("revisionName"):
        prior_serving = route["revisionName"]
        break

if not prior_serving or len(non_zero_routes) > 1:
    sys.exit("Unsupported traffic baseline: traffic is split across multiple revisions or no 100% serving revision found. Developer sandbox deployment requires a single 100% serving baseline.")

# 2. Extract existing env and secrets from service template
existing_env = {}
existing_secrets = {}

template = baseline.get("spec", {}).get("template", {})
containers = template.get("spec", {}).get("containers", [])
if containers and isinstance(containers, list):
    c0 = containers[0]
    env_data = c0.get("env", [])
    if isinstance(env_data, dict):
        for k, v in env_data.items():
            existing_env[k] = str(v)
    elif isinstance(env_data, list):
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

# Safe serialization: use gcloud ^DELIM^ escaping if any value contains a comma
has_comma = any("," in k or "," in v for k, v in merged_env.items())
if has_comma:
    delim = ";;" if not any(";;" in k or ";;" in v for k, v in merged_env.items()) else "@@"
    env_str = f"^{delim}^{delim.join(f'{k}={v}' for k, v in sorted(merged_env.items()))}"
else:
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
); then
    echo "${base_result}" >&2
    return 64
  fi

  # Now verify if prior_serving is safe by inspecting its immutable revision
  local prior_rev
  prior_rev=$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["prior_serving"])' "${base_result}")

  local prior_safe=0
  local prior_rev_json
  if prior_rev_json="$(gcloud run revisions describe "${prior_rev}" --project "${project_id}" --region "${region}" --format=json 2>/dev/null)"; then
    prior_safe=$(PRIOR_JSON="${prior_rev_json}" EXPECTED_SA="${service_account}" python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ["PRIOR_JSON"])
    if not isinstance(data, dict) or not data:
        sys.exit(1)
    spec = data.get("spec", {})
    actual_sa = spec.get("serviceAccountName")
    containers = spec.get("containers", [])
    if not actual_sa and containers:
        actual_sa = containers[0].get("serviceAccountName")
    if actual_sa != os.environ["EXPECTED_SA"]:
        sys.exit(1)

    actual_env = {}
    actual_secrets = {}
    if isinstance(spec.get("env"), dict):
        actual_env.update(spec["env"])
    if isinstance(spec.get("secrets"), dict):
        actual_secrets.update(spec["secrets"])
    if containers:
        c0 = containers[0]
        env_data = c0.get("env", [])
        if isinstance(env_data, dict):
            actual_env.update(env_data)
        elif isinstance(env_data, list):
            for item in env_data:
                if isinstance(item, dict):
                    name = item.get("name")
                    if "value" in item and name:
                        actual_env[name] = str(item["value"])
                    elif "valueFrom" in item and name:
                        ref = item["valueFrom"].get("secretKeyRef", {})
                        sec_name = ref.get("name")
                        sec_key = ref.get("key", "latest")
                        if sec_name:
                            actual_secrets[name] = f"{sec_name}:{sec_key}"

    if actual_env.get("DB_NAME") != "dtd_sandbox":
        sys.exit(1)
    for flag in ["ENABLE_TRAINER_BILLING_CHECKOUT", "ENABLE_OPS_STRIPE_REFUNDS", "OPS_SELF_HEALING_ENABLED"]:
        if actual_env.get(flag) != "0":
            sys.exit(1)
    if actual_secrets.get("ADMIN_PASS") != "dtd-admin-pass:4":
        sys.exit(1)
    if actual_secrets.get("TRAINER_ACTION_TOKEN_SECRET") != "dtd-trainer-action-token-secret:2":
        sys.exit(1)
    print("1")
except Exception:
    print("0")
PY
    )
  fi

  # Augment base_result with prior_serving_safe
  BASE_RESULT="${base_result}" PRIOR_SAFE="${prior_safe:-0}" python3 - <<'PY'
import json, os
d = json.loads(os.environ["BASE_RESULT"])
d["prior_serving_safe"] = int(os.environ.get("PRIOR_SAFE", "0") == "1")
print(json.dumps(d))
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

  local candidate_url
  if ! candidate_url=$(SERVICE_JSON="${service_json}" EXPECTED_REVISION="${expected_revision}" TARGET_TAG="${tag}" python3 - <<'PY'
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
); then
    echo "${candidate_url}" >&2
    return 64
  fi
  echo "${candidate_url}"
}

verify_candidate_invariants() {
  local service_name="$1"
  local project_id="$2"
  local region="$3"
  local expected_revision="$4"

  # Query exact immutable revision metadata
  local rev_json
  if ! rev_json="$(gcloud run revisions describe "${expected_revision}" --project "${project_id}" --region "${region}" --format=json 2>&1)"; then
    echo "Could not inspect immutable candidate revision ${expected_revision}: ${rev_json}" >&2
    return 64
  fi

  local verify_result
  if ! verify_result=$(REVISION_JSON="${rev_json}" EXPECTED_REVISION="${expected_revision}" EXPECTED_SERVICE_ACCOUNT="${SERVICE_ACCOUNT}" python3 - <<'PY'
import json, os, sys

try:
    data = json.loads(os.environ["REVISION_JSON"])
except Exception as e:
    sys.exit(f"Failed to parse candidate revision JSON: {e}")

if not isinstance(data, dict) or not data:
    sys.exit("Candidate revision metadata is empty or not a dictionary")

expected_rev = os.environ["EXPECTED_REVISION"]
expected_sa = os.environ["EXPECTED_SERVICE_ACCOUNT"]

# 1. Readiness check: must be explicitly Ready (or ready boolean in synthetic spec)
status = data.get("status", {})
conditions = status.get("conditions", [])
ready = None
for c in conditions:
    if c.get("type") == "Ready":
        ready = (c.get("status") == "True")
        break

spec = data.get("spec", {})
if not isinstance(spec, dict) or not spec:
    sys.exit("Candidate revision spec is missing or empty")

if ready is None and "ready" in spec:
    ready = bool(spec["ready"])

if ready is not True:
    sys.exit(f"Candidate revision '{expected_rev}' is not in ready state")

# 2. Service account check
actual_sa = spec.get("serviceAccountName")
containers = spec.get("containers", [])
if not actual_sa and containers and isinstance(containers, list):
    actual_sa = containers[0].get("serviceAccountName")

if not actual_sa or actual_sa != expected_sa:
    sys.exit(f"Candidate serviceAccountName mismatch: got '{actual_sa}', expected '{expected_sa}'")

# 3. Image check
actual_image = spec.get("image")
if not actual_image and containers and isinstance(containers, list):
    actual_image = containers[0].get("image")

if not actual_image:
    sys.exit(f"Candidate revision '{expected_rev}' has no container image defined")

# 4. Extract environment variables and secrets
actual_env = {}
actual_secrets = {}

if isinstance(spec.get("env"), dict):
    actual_env.update(spec["env"])
if isinstance(spec.get("secrets"), dict):
    actual_secrets.update(spec["secrets"])

if containers and isinstance(containers, list):
    c0 = containers[0]
    env_data = c0.get("env", [])
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

if not actual_env:
    sys.exit(f"Candidate revision '{expected_rev}' has no environment variables defined")

if actual_env.get("DB_NAME") != "dtd_sandbox":
    sys.exit(f"Candidate DB_NAME invariant failure: got '{actual_env.get('DB_NAME')}', expected 'dtd_sandbox'")

for flag in ["ENABLE_TRAINER_BILLING_CHECKOUT", "ENABLE_OPS_STRIPE_REFUNDS", "OPS_SELF_HEALING_ENABLED"]:
    if actual_env.get(flag) != "0":
        sys.exit(f"Candidate safety flag failure: {flag} is '{actual_env.get(flag)}', expected '0'")

if not actual_secrets:
    sys.exit(f"Candidate revision '{expected_rev}' has no secret bindings defined")

if actual_secrets.get("ADMIN_PASS") != "dtd-admin-pass:4":
    sys.exit(f"Candidate ADMIN_PASS invariant failure: got '{actual_secrets.get('ADMIN_PASS')}', expected 'dtd-admin-pass:4'")

if actual_secrets.get("TRAINER_ACTION_TOKEN_SECRET") != "dtd-trainer-action-token-secret:2":
    sys.exit(f"Candidate TRAINER_ACTION_TOKEN_SECRET invariant failure: got '{actual_secrets.get('TRAINER_ACTION_TOKEN_SECRET')}', expected 'dtd-trainer-action-token-secret:2'")

print("CANDIDATE_INVARIANTS_VERIFIED")
PY
); then
    echo "${verify_result}" >&2
    return 64
  fi
  echo "${verify_result}"
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
  PRIOR_SERVING_SAFE="$(python3 -c 'import json, sys; print(json.loads(sys.argv[1]).get("prior_serving_safe", 0))' "${CONFIG_RESULT}")"
  DEPLOY_SET_ENV="$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["set_env_vars"])' "${CONFIG_RESULT}")"
  DEPLOY_SET_SECRETS="$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["set_secrets"])' "${CONFIG_RESULT}")"
  echo "Prior serving revision: ${PRIOR_SERVING_REVISION} (verified safe for recovery: ${PRIOR_SERVING_SAFE})"

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

  # Concurrency check: Verify current serving traffic has not changed since baseline
  local current_traffic_json
  current_traffic_json="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format=json 2>&1)"
  local current_serving
  current_serving=$(CURRENT_JSON="${current_traffic_json}" python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ["CURRENT_JSON"])
    routes = data.get("status", {}).get("traffic", [])
    for r in routes:
        if int(r.get("percent") or 0) == 100 and r.get("revisionName"):
            print(r["revisionName"])
            sys.exit(0)
    print("")
except Exception:
    print("")
PY
  )

  if [ -n "${current_serving}" ] && [ "${current_serving}" != "${PRIOR_SERVING_REVISION}" ]; then
    echo "🚨 Concurrency conflict: current serving revision is '${current_serving}', but baseline was '${PRIOR_SERVING_REVISION}'." >&2
    echo "Aborting promotion to prevent overwriting another operator's traffic." >&2
    exit 1
  fi

  set +e
  local update_output
  update_output="$(gcloud run services update-traffic "${SERVICE_NAME}" \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --to-revisions "${EXPECTED_REVISION}=100" 2>&1)"
  local update_status=$?
  set -e

  # Reconcile actual routing state regardless of command returncode
  local observed_state
  observed_state="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format=json 2>/dev/null || true)"
  local actual_promoted
  actual_promoted=$(OBSERVED_JSON="${observed_state}" EXPECTED_REV="${EXPECTED_REVISION}" python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ["OBSERVED_JSON"])
    routes = data.get("status", {}).get("traffic", [])
    for r in routes:
        if r.get("revisionName") == os.environ["EXPECTED_REV"] and int(r.get("percent") or 0) == 100:
            print("1")
            sys.exit(0)
    print("0")
except Exception:
    print("0")
PY
  )

  if [ "${actual_promoted}" = "1" ]; then
    TRAFFIC_PROMOTED=1
  fi

  if [ "${update_status}" -ne 0 ]; then
    echo "Traffic promotion command failed with status ${update_status}: ${update_output}" >&2
    exit "${update_status}"
  fi

  validate_deployed_traffic_response "${observed_state}" "${EXPECTED_REVISION}"

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
