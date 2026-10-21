#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${repo_root}/scripts/deploy_sandbox.sh"

validate_health_response '{"ok":true,"database":"available"}'

validate_deployed_traffic_response '{"status":{"latestCreatedRevisionName":"dtd-api-dev-00028-ttz","latestReadyRevisionName":"dtd-api-dev-00028-ttz","traffic":[{"revisionName":"dtd-api-dev-00028-ttz","percent":100}]}}'

for state in \
  '{"status":{"latestCreatedRevisionName":"","latestReadyRevisionName":"dtd-api-dev-00027-yob","traffic":[{"revisionName":"dtd-api-dev-00027-yob","percent":100}]}}' \
  '{"status":{"latestCreatedRevisionName":"dtd-api-dev-00028-ttz","latestReadyRevisionName":"dtd-api-dev-00027-yob","traffic":[{"revisionName":"dtd-api-dev-00027-yob","percent":100}]}}' \
  '{"status":{"latestCreatedRevisionName":"dtd-api-dev-00028-ttz","latestReadyRevisionName":"dtd-api-dev-00028-ttz","traffic":[{"revisionName":"dtd-api-dev-00027-yob","percent":100}]}}'; do
  if validate_deployed_traffic_response "${state}" >/dev/null 2>&1; then
    echo "Expected sandbox traffic validation to reject: ${state}" >&2
    exit 1
  fi
done

for response in '{"ok":false,"database":"available"}' '{"ok":true,"database":"unavailable"}' 'not-json'; do
  if validate_health_response "${response}" >/dev/null 2>&1; then
    echo "Expected sandbox health validation to reject: ${response}" >&2
    exit 1
  fi
done

if bash "${repo_root}/scripts/deploy_sandbox.sh" --skip-tests >/dev/null 2>&1; then
  echo "Expected sandbox deployment to reject bypass arguments" >&2
  exit 1
fi

if grep -Eq '^[[:space:]]*bash .*setup_sandbox_ingestion\.sh' "${repo_root}/scripts/deploy_sandbox.sh"; then
  echo "Deployment must not silently invoke scheduler/IAM provisioning" >&2
  exit 1
fi

for setting in ENABLE_TRAINER_BILLING_CHECKOUT=0 OPS_SELF_HEALING_ENABLED=0; do
  if ! grep -Fq "${setting}" "${repo_root}/scripts/deploy_sandbox.sh"; then
    echo "Sandbox deployment must explicitly keep ${setting}" >&2
    exit 1
  fi
done

for web_contract in '--to-latest' 'latestCreatedRevisionName' 'latestReadyRevisionName' 'EXPECTED_BUNDLE'; do
  if ! grep -Fq -- "${web_contract}" "${repo_root}/scripts/deploy_sandbox_frontend.sh"; then
    echo "Sandbox frontend deployment must verify ${web_contract}" >&2
    exit 1
  fi
done

REPO_ROOT="${repo_root}" python3 - <<'PY'
import os
import pathlib
import re

pattern = r"""/(?:assets/index|static/js/main)[^\"]*\.js"""
sample = '<script type="module" src="/assets/index-A1b2C3.js"></script>'
match = re.search(pattern, sample)
assert match and match.group(0) == "/assets/index-A1b2C3.js", match
index_html = pathlib.Path(os.environ["REPO_ROOT"]) / "frontend/build/index.html"
assert index_html.is_file(), f"Expected built index at {index_html}"
print("Sandbox frontend bundle parser: PASS")
PY

if ! grep -Fq -- '--update-headers="Content-Type=application/json"' "${repo_root}/scripts/setup_sandbox_ingestion.sh"; then
  echo "Scheduler provisioning must send JSON payloads to the FastAPI endpoint" >&2
  exit 1
fi

echo "SANDBOX_DEPLOY_CONTRACT=PASS"
