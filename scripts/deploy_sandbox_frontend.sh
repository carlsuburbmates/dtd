#!/usr/bin/env bash
set -euo pipefail

# Deploy the isolated developer web surface. It never targets Firebase,
# production Cloud Run, a custom domain, billing, or a public release channel.
PROJECT_ID="dogtrainersdirectory-dev"
REGION="australia-southeast1"
SERVICE_NAME="dtd-web-dev"
API_URL="https://dtd-api-dev-625222421634.${REGION}.run.app"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

WEB_URL="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
curl --fail --silent --show-error --location --max-time 15 "${WEB_URL}/" | grep -q '<div id="root">'
MAIN_BUNDLE=$(curl --fail --silent --show-error --location --max-time 15 "${WEB_URL}/" | sed -n 's/.*\(\/static\/js\/main\.[^"]*\.js\).*/\1/p')
curl --fail --silent --show-error --location --max-time 15 "${WEB_URL}${MAIN_BUNDLE}" | grep -q "${API_URL}"
echo "Sandbox frontend verified: ${WEB_URL} -> ${API_URL}"
