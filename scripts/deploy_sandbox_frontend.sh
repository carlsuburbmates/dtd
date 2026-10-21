#!/usr/bin/env bash
set -euo pipefail

# Deploy the isolated developer web surface. It never targets Firebase,
# production Cloud Run, a custom domain, billing, or a public release channel.
PROJECT_ID="dogtrainersdirectory-dev"
REGION="australia-southeast1"
SERVICE_NAME="dtd-web-dev"
API_URL="https://dtd-api-dev-625222421634.${REGION}.run.app"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

validate_deployed_traffic_response() {
  SERVICE_STATE="$1" python3 - <<'PY'
import json
import os

try:
    response = json.loads(os.environ["SERVICE_STATE"])
except (KeyError, json.JSONDecodeError) as error:
    raise SystemExit(f"Sandbox web service state was not valid JSON: {error}")

state = response.get("status", response)
latest_created = state.get("latestCreatedRevisionName") or ""
latest_ready = state.get("latestReadyRevisionName") or ""
traffic = state.get("traffic") or []

if not latest_created:
    raise SystemExit("Sandbox web service has no created revision")
if latest_ready != latest_created:
    raise SystemExit("Latest sandbox web revision is not ready")
if not any(
    route.get("revisionName") == latest_created and int(route.get("percent") or 0) == 100
    for route in traffic
):
    raise SystemExit("Latest sandbox web revision is not receiving 100 percent of traffic")
PY
}

if [ "$#" -ne 0 ]; then
  echo "Usage: bash scripts/deploy_sandbox_frontend.sh" >&2
  exit 64
fi

(
  cd "${REPO_ROOT}/frontend"
  yarn build
)

gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --source "${REPO_ROOT}/frontend" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2

# Existing service traffic can remain pinned to a named revision after deploy.
# Promote the newly created revision explicitly, then verify identity and traffic.
gcloud run services update-traffic "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --to-latest

SERVICE_STATE="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="json(status.latestCreatedRevisionName,status.latestReadyRevisionName,status.traffic)")"
validate_deployed_traffic_response "${SERVICE_STATE}"

WEB_URL="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
HTML="$(curl --fail --silent --show-error --location --max-time 15 "${WEB_URL}/")"
case "${HTML}" in
  *'<div id="root">'*) ;;
  *)
    echo "Sandbox frontend HTML does not contain the application root" >&2
    exit 1
    ;;
esac
MAIN_BUNDLE="$(python3 -c 'import re, sys; match = re.search(r"/(?:assets/index|static/js/main)[^\"]*\.js", sys.stdin.read()); print(match.group(0) if match else "")' <<< "${HTML}")"
if [ -z "${MAIN_BUNDLE}" ]; then
  echo "Could not find the frontend JavaScript bundle in the sandbox HTML" >&2
  exit 1
fi
EXPECTED_BUNDLE="$(REPO_ROOT="${REPO_ROOT}" python3 - <<'PY'
import os
import pathlib
import re

html = (pathlib.Path(os.environ["REPO_ROOT"]) / "frontend/build/index.html").read_text()
match = re.search(r"""/(?:assets/index|static/js/main)[^\"]*\.js""", html)
print(match.group(0) if match else "")
PY
)"
if [ -z "${EXPECTED_BUNDLE}" ] || [ "${MAIN_BUNDLE}" != "${EXPECTED_BUNDLE}" ]; then
  echo "Sandbox frontend is not serving the bundle built from this checkout" >&2
  exit 1
fi
BUNDLE_CONTENT="$(curl --fail --silent --show-error --location --max-time 15 "${WEB_URL}${MAIN_BUNDLE}")"
if [[ "${BUNDLE_CONTENT}" != *"${API_URL}"* ]]; then
  echo "Sandbox frontend bundle does not use the isolated developer API origin" >&2
  exit 1
fi
echo "Sandbox frontend verified: ${WEB_URL} -> ${API_URL}"
