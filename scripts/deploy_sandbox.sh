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
CANDIDATE_TAG=""
EXPECTED_REVISION=""
EXPECTED_IMAGE=""
CONFIG_RESULT=""
PRIOR_SERVING_REVISION=""
PRIOR_SERVING_SAFE=0
DEPLOY_ATTEMPTED=0
PROMOTION_ATTEMPTED=0
SUCCESSFUL_COMPLETION=0

# Parse the observed routes once, preserving the distinction between absent,
# split and unreadable state. No routing write may infer ownership from silence.
service_routes() {
  RESOURCE_JSON="$1" python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ['RESOURCE_JSON'])
    routes = data['status']['traffic']
    if not isinstance(routes, list) or not routes:
        raise ValueError()
    weights, tags = {}, {}
    for route in routes:
        name = route.get('revisionName')
        percent = route.get('percent', 0)
        if not isinstance(name, str) or not name or type(percent) is not int or not 0 <= percent <= 100:
            raise ValueError()
        if percent:
            weights[name] = weights.get(name, 0) + percent
        if 'tag' in route:
            tag = route['tag']
            if not isinstance(tag, str) or not tag or tag in tags:
                raise ValueError()
            tags[tag] = {'revision': name, 'url': route.get('url')}
    if sum(weights.values()) != 100:
        raise ValueError()
    serving = next(iter(weights)) if len(weights) == 1 else None
    print(json.dumps({'serving': serving, 'tags': tags}))
except (ValueError, KeyError, TypeError, AttributeError):
    sys.exit('Cloud Run routing evidence is missing or invalid')
PY
}

serving_revision() {
  local routes
  routes="$(service_routes "$1")" || return 64
  ROUTES_JSON="${routes}" python3 - <<'PY'
import json, os, sys
serving = json.loads(os.environ['ROUTES_JSON'])['serving']
if not serving:
    sys.exit('Cloud Run routing is split; no exclusive serving revision is proven')
print(serving)
PY
}

tag_owner() {
  local routes
  routes="$(service_routes "$1")" || return 64
  ROUTES_JSON="${routes}" TARGET_TAG="$2" python3 - <<'PY'
import json, os
route = json.loads(os.environ['ROUTES_JSON'])['tags'].get(os.environ['TARGET_TAG'])
print(route['revision'] if route else '')
PY
}

read_service() {
  gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format=json
}

# Real Cloud Run v1 Service/Revision configuration only. No fixture fallbacks.
resource_configuration() {
  RESOURCE_JSON="$1" RESOURCE_KIND="$2" python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ['RESOURCE_JSON'])
    resource = data['spec']['template'] if os.environ['RESOURCE_KIND'] == 'service' else data
    spec = resource['spec']
    name = resource['metadata']['name']
    account = spec['serviceAccountName']
    containers = spec['containers']
    if not isinstance(name, str) or not name or not account or not isinstance(containers, list) or len(containers) != 1:
        raise ValueError()
    image = containers[0]['image']
    entries = containers[0]['env']
    if not image or not isinstance(entries, list) or not entries:
        raise ValueError()
    env, secrets = {}, {}
    for item in entries:
        key = item['name']
        if not isinstance(key, str) or not key or key in env or key in secrets:
            raise ValueError()
        if 'value' in item and 'valueFrom' not in item and isinstance(item['value'], str):
            env[key] = item['value']
        elif 'valueFrom' in item and 'value' not in item:
            ref = item['valueFrom']['secretKeyRef']
            if not ref['name'] or not ref['key']:
                raise ValueError()
            secrets[key] = ref['name'] + ':' + str(ref['key'])
        else:
            raise ValueError()
    print(json.dumps({'name': name, 'account': account, 'image': image, 'env': env, 'secrets': secrets}))
except (ValueError, KeyError, TypeError, AttributeError):
    sys.exit('Cloud Run configuration evidence is incomplete or unsupported')
PY
}

validate_revision() {
  local config
  config="$(resource_configuration "$1" revision)" || return 64
  REVISION_JSON="$1" CONFIG_JSON="${config}" EXPECTED_REV="$2" EXPECTED_SA="${SERVICE_ACCOUNT}" EXPECTED_IMAGE_ARG="${3:-}" INTENDED_JSON="${4:-}" python3 - <<'PY'
import json, os, sys
revision = json.loads(os.environ['REVISION_JSON'])
cfg = json.loads(os.environ['CONFIG_JSON'])
if cfg['name'] != os.environ['EXPECTED_REV']:
    sys.exit('Revision identity does not match expected revision')
conditions = revision.get('status', {}).get('conditions', [])
if not any(c.get('type') == 'Ready' and c.get('status') == 'True' for c in conditions):
    sys.exit('Expected revision is not explicitly Ready')
if cfg['account'] != os.environ['EXPECTED_SA']:
    sys.exit('Revision runtime identity is not the sandbox identity')
if cfg['env'].get('DB_NAME') != 'dtd_sandbox':
    sys.exit('Revision is not scoped to the sandbox database')
for key in ('ENABLE_TRAINER_BILLING_CHECKOUT', 'ENABLE_OPS_STRIPE_REFUNDS', 'OPS_SELF_HEALING_ENABLED'):
    if cfg['env'].get(key) != '0':
        sys.exit('Revision safety flags are not disabled')
for key, value in {'ADMIN_PASS':'dtd-admin-pass:4', 'TRAINER_ACTION_TOKEN_SECRET':'dtd-trainer-action-token-secret:2'}.items():
    if cfg['secrets'].get(key) != value:
        sys.exit('Revision replacement secret bindings are not pinned')
expected_image = os.environ['EXPECTED_IMAGE_ARG']
if expected_image:
    if cfg['image'] != expected_image:
        sys.exit('Revision image differs from this deployment build result')
    digest = revision.get('status', {}).get('imageDigest')
    if digest not in (expected_image, expected_image.split('@')[-1]):
        sys.exit('Revision resolved image digest does not match deployment evidence')
if os.environ['INTENDED_JSON']:
    intended = json.loads(os.environ['INTENDED_JSON'])
    if cfg['env'] != intended['merged_env'] or cfg['secrets'] != intended['merged_secrets']:
        sys.exit('Revision configuration differs from the complete permitted deployment delta')
print(cfg['image'])
PY
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
  local current expected="${2:-}"
  current="$(serving_revision "$1")" || return 64
  if [ -z "${expected}" ]; then
    expected="$(STATE_JSON="$1" python3 - <<'PY'
import json, os, sys
status = json.loads(os.environ['STATE_JSON'])['status']
created, ready = status.get('latestCreatedRevisionName'), status.get('latestReadyRevisionName')
if not created or created != ready:
    sys.exit('Latest revision is not ready')
print(created)
PY
)" || return 64
  fi
  [ "${current}" = "${expected}" ] || { echo 'Serving traffic does not match expected revision' >&2; return 64; }
}

capture_and_merge_configuration() {
  local baseline config prior prior_json prior_safe=0
  baseline="$(gcloud run services describe "$1" --project "$2" --region "$3" --format=json)" || return 64
  prior="$(serving_revision "${baseline}")" || return 64
  config="$(resource_configuration "${baseline}" service)" || return 64
  # Do not adopt an unserved template from a concurrent deployment as baseline.
  [ "$(CONFIG_JSON="${config}" python3 -c 'import json,os; print(json.loads(os.environ["CONFIG_JSON"])["name"])')" = "${prior}" ] || { echo 'Baseline template and serving revision differ' >&2; return 64; }
  prior_json="$(gcloud run revisions describe "${prior}" --project "$2" --region "$3" --format=json)" || return 64
  if validate_revision "${prior_json}" "${prior}" >/dev/null 2>&1; then prior_safe=1; fi
  # Even an unsafe predecessor cannot supply a fabricated or unreadable config.
  local prior_config
  prior_config="$(resource_configuration "${prior_json}" revision)" || return 64
  CONFIG_JSON="${config}" PRIOR_CONFIG_JSON="${prior_config}" PRIOR_REV="${prior}" PRIOR_SAFE="${prior_safe}" EXPECTED_SA="$4" SERVICE_URL_ARG="$5" python3 - <<'PY'
import json, os, sys
cfg = json.loads(os.environ['CONFIG_JSON'])
prior = json.loads(os.environ['PRIOR_CONFIG_JSON'])
if cfg != prior:
    sys.exit('Baseline service and immutable serving configuration differ')
if cfg['account'] != os.environ['EXPECTED_SA']:
    sys.exit('Baseline runtime identity differs from the sandbox identity')
baseline_config = json.loads(json.dumps(cfg))
env, secrets = cfg['env'], cfg['secrets']
if not all(k in secrets for k in ('MONGO_URL','ADMIN_PASS','TRAINER_ACTION_TOKEN_SECRET')):
    sys.exit('Baseline required secret references are missing')
if not all(k in env for k in ('DB_NAME','STRIPE_KEY_UPDATED','STRIPE_LIVE_ANCHOR_AT')):
    sys.exit('Baseline database or cohort evidence is missing')
# Preserve unrelated integrations, numeric versions and cohort values exactly.
env.update({'DB_NAME':'dtd_sandbox','SENTRY_ENVIRONMENT':'staging','DISABLE_AUTONOMY':'1',
            'ENABLE_STARTUP_SEEDS':'0','AUTONOMY_LOOP_OWNER':'none',
            'ENABLE_TRAINER_BILLING_CHECKOUT':'0','ENABLE_OPS_STRIPE_REFUNDS':'0',
            'OPS_SELF_HEALING_ENABLED':'0','CLOUD_SCHEDULER_OIDC_SERVICE_ACCOUNT':os.environ['EXPECTED_SA'],
            'CLOUD_SCHEDULER_OIDC_AUDIENCE':os.environ['SERVICE_URL_ARG']})
secrets.update({'ADMIN_PASS':'dtd-admin-pass:4','TRAINER_ACTION_TOKEN_SECRET':'dtd-trainer-action-token-secret:2'})
def serialize(values):
    delim = ';;'
    while any(delim in k or delim in v for k,v in values.items()):
        delim += ';'
    return '^' + delim + '^' + delim.join(k+'='+v for k,v in sorted(values.items()))
print(json.dumps({'prior_serving':os.environ['PRIOR_REV'], 'prior_serving_safe':int(os.environ['PRIOR_SAFE']),
                  'baseline_config':baseline_config, 'merged_env':env,'merged_secrets':secrets,
                  'set_env_vars':serialize(env),'set_secrets':serialize(secrets)}))
PY
}

resolve_and_verify_candidate_url() {
  local state routes
  state="$(gcloud run services describe "$1" --project "$2" --region "$3" --format=json)" || return 64
  routes="$(service_routes "${state}")" || return 64
  ROUTES_JSON="${routes}" EXPECTED_REV="$4" TARGET_TAG="${5:-${CANDIDATE_TAG}}" python3 - <<'PY'
import json, os, sys
route = json.loads(os.environ['ROUTES_JSON'])['tags'].get(os.environ['TARGET_TAG'])
if not route or route['revision'] != os.environ['EXPECTED_REV']:
    sys.exit('Candidate tag is absent or no longer owned by this revision')
url = route.get('url')
if not isinstance(url, str) or not url.startswith('https://'):
    sys.exit('Provider returned no candidate URL; refusing to invent one')
print(url)
PY
}

verify_candidate_invariants() {
  local revision_json
  [ -n "${5:-}" ] && [ -n "${6:-}" ] || { echo 'Expected build image/configuration evidence is required' >&2; return 64; }
  revision_json="$(gcloud run revisions describe "$4" --project "$2" --region "$3" --format=json)" || return 64
  validate_revision "${revision_json}" "$4" "$5" "$6" >/dev/null || return 64
}

deployment_image() {
  local config
  config="$(resource_configuration "$1" service)" || return 64
  CONFIG_JSON="${config}" DEPLOY_JSON="$1" EXPECTED_REV="${EXPECTED_REVISION}" EXPECTED_SA="${SERVICE_ACCOUNT}" INTENDED_JSON="${CONFIG_RESULT}" SERVICE_NAME_ARG="${SERVICE_NAME}" python3 - <<'PY'
import json, os, re, sys
cfg, data = json.loads(os.environ['CONFIG_JSON']), json.loads(os.environ['DEPLOY_JSON'])
intended = json.loads(os.environ['INTENDED_JSON'])
if data.get('metadata',{}).get('name') != os.environ['SERVICE_NAME_ARG'] or cfg['name'] != os.environ['EXPECTED_REV']:
    sys.exit('Deploy result is not the expected service/revision')
status = data.get('status',{})
if status.get('latestCreatedRevisionName') != cfg['name'] or status.get('latestReadyRevisionName') != cfg['name']:
    sys.exit('Deploy operation did not return a ready exact candidate')
if not re.fullmatch(r'.+@sha256:[0-9a-f]{64}', cfg['image']):
    sys.exit('Source deploy result did not return a digest-pinned build image')
if cfg['account'] != os.environ['EXPECTED_SA'] or cfg['env'] != intended['merged_env'] or cfg['secrets'] != intended['merged_secrets']:
    sys.exit('Deploy result configuration differs from the permitted delta')
print(cfg['image'])
PY
}

cleanup_and_recover() {
  local exit_code=$? state current owner after cleanup_failed=0
  trap - EXIT
  set +e
  if [ "${PROMOTION_ATTEMPTED}" -eq 1 ] && [ "${SUCCESSFUL_COMPLETION}" -ne 1 ]; then
    state="$(read_service)"
    if [ "$?" -ne 0 ] || ! current="$(serving_revision "${state}")"; then
      echo 'Guarded recovery: routing UNKNOWN or split; no rollback write authorised.' >&2
    elif [ "${current}" = "${PRIOR_SERVING_REVISION}" ]; then
      echo 'Verified prior traffic retained; no rollback needed.' >&2
    elif [ "${current}" != "${EXPECTED_REVISION}" ]; then
      echo "Guarded recovery: observed foreign traffic ${current}; preserving it." >&2
    elif [ "${PRIOR_SERVING_SAFE}" -ne 1 ]; then
      echo "Guarded recovery: observed candidate ${current}; prior revision is unsafe, no rollback authorised." >&2
    else
      gcloud run services update-traffic "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --to-revisions "${PRIOR_SERVING_REVISION}=100" >/dev/null
      local rollback_status=$?
      after="$(read_service)"
      if [ "$?" -eq 0 ] && validate_deployed_traffic_response "${after}" "${PRIOR_SERVING_REVISION}" && validate_health_response "$(curl --fail --silent --show-error --location --max-time 15 "${SERVICE_URL}/api/health")"; then
        echo "Verified safe recovery to ${PRIOR_SERVING_REVISION} (command status ${rollback_status})." >&2
      else
        echo 'Guarded recovery: rollback outcome NOT_VERIFIED; inspect observed routing before further writes.' >&2
      fi
    fi
  fi
  if [ "${DEPLOY_ATTEMPTED}" -eq 1 ]; then
    state="$(read_service)"
    if [ "$?" -ne 0 ] || ! owner="$(tag_owner "${state}" "${CANDIDATE_TAG}")"; then
      echo 'Temporary tag ownership UNKNOWN; cleanup NOT_VERIFIED.' >&2
      cleanup_failed=1
    elif [ -z "${owner}" ]; then
      echo 'Verified temporary tag absent.' >&2
    elif [ "${owner}" != "${EXPECTED_REVISION}" ]; then
      echo 'Temporary tag belongs to another revision; preserving foreign routing.' >&2
    else
      gcloud run services update-traffic "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --remove-tags "${CANDIDATE_TAG}" >/dev/null
      after="$(read_service)"
      if [ "$?" -ne 0 ] || ! owner="$(tag_owner "${after}" "${CANDIDATE_TAG}")" || [ -n "${owner}" ]; then
        echo 'Temporary tag cleanup NOT_VERIFIED.' >&2
        cleanup_failed=1
      fi
    fi
  fi
  if [ "${exit_code}" -eq 0 ] && { [ "${SUCCESSFUL_COMPLETION}" -ne 1 ] || [ "${cleanup_failed}" -ne 0 ]; }; then exit_code=1; fi
  exit "${exit_code}"
}

main() {
  if [ "$#" -ne 0 ]; then echo 'Usage: bash scripts/deploy_sandbox.sh' >&2; exit 64; fi
  trap cleanup_and_recover EXIT
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  cd "${REPO_ROOT}"
  DEPLOY_SOURCE_SHA="$(resolve_deploy_source_sha "${REPO_ROOT}")"
  local run_id
  run_id="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:10])')"
  REVISION_SUFFIX="r8-${DEPLOY_SOURCE_SHA:0:8}-${run_id}"
  EXPECTED_REVISION="${SERVICE_NAME}-${REVISION_SUFFIX}"
  CANDIDATE_TAG="verify-${run_id}"
  echo "Sandbox source ${DEPLOY_SOURCE_SHA}; candidate ${EXPECTED_REVISION}; temporary tag ${CANDIDATE_TAG}"
  validate_preflight_interpreter
  validate_ingestion_scheduler_paused "${PROJECT_ID}" "${REGION}"
  python3 -m py_compile backend/server.py backend/worker.py backend/services/*.py
  node scripts/check_prelaunch_release_gate.js
  "${PREFLIGHT_PYTHON}" backend/scripts/run_isolated_integration_suite.py
  CONFIG_RESULT="$(capture_and_merge_configuration "${SERVICE_NAME}" "${PROJECT_ID}" "${REGION}" "${SERVICE_ACCOUNT}" "${SERVICE_URL}")"
  PRIOR_SERVING_REVISION="$(RESULT="${CONFIG_RESULT}" python3 -c 'import json,os; print(json.loads(os.environ["RESULT"])["prior_serving"])')"
  PRIOR_SERVING_SAFE="$(RESULT="${CONFIG_RESULT}" python3 -c 'import json,os; print(json.loads(os.environ["RESULT"])["prior_serving_safe"])')"
  local deploy_env deploy_secrets deploy_result candidate_url_check current state
  deploy_env="$(RESULT="${CONFIG_RESULT}" python3 -c 'import json,os; print(json.loads(os.environ["RESULT"])["set_env_vars"])')"
  deploy_secrets="$(RESULT="${CONFIG_RESULT}" python3 -c 'import json,os; print(json.loads(os.environ["RESULT"])["set_secrets"])')"
  [ "$(resolve_deploy_source_sha "${REPO_ROOT}")" = "${DEPLOY_SOURCE_SHA}" ] || { echo 'Source changed during preflight' >&2; exit 64; }
  state="$(read_service)"
  [ "$(serving_revision "${state}")" = "${PRIOR_SERVING_REVISION}" ] || { echo 'Baseline traffic changed before build' >&2; exit 64; }
  local current_config
  current_config="$(resource_configuration "${state}" service)"
  CURRENT_CONFIG="${current_config}" INTENDED_JSON="${CONFIG_RESULT}" python3 - <<'PY_CHECK'
import json, os, sys
if json.loads(os.environ['CURRENT_CONFIG']) != json.loads(os.environ['INTENDED_JSON'])['baseline_config']:
    sys.exit('Baseline configuration changed before build; refusing to overwrite it')
PY_CHECK
  [ -z "$(tag_owner "${state}" "${CANDIDATE_TAG}")" ] || { echo 'Temporary tag already exists; refusing to claim it' >&2; exit 64; }
  DEPLOY_ATTEMPTED=1
  deploy_result="$(gcloud run deploy "${SERVICE_NAME}" \
    --project "${PROJECT_ID}" --region "${REGION}" \
    --revision-suffix "${REVISION_SUFFIX}" --source backend --allow-unauthenticated \
    --no-traffic --tag "${CANDIDATE_TAG}" --service-account "${SERVICE_ACCOUNT}" \
    --set-env-vars "${deploy_env}" --set-secrets "${deploy_secrets}" \
    --cpu 1 --memory 1Gi --timeout 300 --min-instances 0 --max-instances 2 --format=json)"
  EXPECTED_IMAGE="$(deployment_image "${deploy_result}")"
  verify_candidate_invariants "${SERVICE_NAME}" "${PROJECT_ID}" "${REGION}" "${EXPECTED_REVISION}" "${EXPECTED_IMAGE}" "${CONFIG_RESULT}"
  CANDIDATE_URL="$(resolve_and_verify_candidate_url "${SERVICE_NAME}" "${PROJECT_ID}" "${REGION}" "${EXPECTED_REVISION}" "${CANDIDATE_TAG}")"
  CANDIDATE_HEALTH=$(curl --fail --silent --show-error --location --max-time 15 "${CANDIDATE_URL}/api/health")
  validate_health_response "${CANDIDATE_HEALTH}"
  candidate_url_check="$(resolve_and_verify_candidate_url "${SERVICE_NAME}" "${PROJECT_ID}" "${REGION}" "${EXPECTED_REVISION}" "${CANDIDATE_TAG}")"
  [ "${candidate_url_check}" = "${CANDIDATE_URL}" ] || { echo 'Candidate route changed during health check' >&2; exit 64; }
  state="$(read_service)"
  current="$(serving_revision "${state}")" || exit 64
  [ "${current}" = "${PRIOR_SERVING_REVISION}" ] || { echo 'Foreign traffic change; refusing promotion' >&2; exit 64; }
  [ "$(tag_owner "${state}" "${CANDIDATE_TAG}")" = "${EXPECTED_REVISION}" ] || { echo 'Candidate tag changed before cutover' >&2; exit 64; }
  PROMOTION_ATTEMPTED=1
  gcloud run services update-traffic "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --to-revisions "${EXPECTED_REVISION}=100"
  state="$(read_service)"
  validate_deployed_traffic_response "${state}" "${EXPECTED_REVISION}"
  HEALTH_RESPONSE=$(curl --fail --silent --show-error --location --max-time 15 "${SERVICE_URL}/api/health")
  validate_health_response "${HEALTH_RESPONSE}"
  state="$(read_service)"
  validate_deployed_traffic_response "${state}" "${EXPECTED_REVISION}"
  SUCCESSFUL_COMPLETION=1
  echo "Verified ${EXPECTED_REVISION} at 100% traffic; build image ${EXPECTED_IMAGE}."
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
