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

if ! grep -Fq 'DTD_PREFLIGHT_PYTHON' "${repo_root}/scripts/deploy_sandbox.sh" || ! grep -Fq '"${PREFLIGHT_PYTHON}" backend/scripts/run_isolated_integration_suite.py' "${repo_root}/scripts/deploy_sandbox.sh"; then
  echo "Sandbox deployment must support an explicit isolated preflight interpreter" >&2
  exit 1
fi

invalid_python_output="$(DTD_PREFLIGHT_PYTHON="${repo_root}/does-not-exist" bash "${repo_root}/scripts/deploy_sandbox.sh" 2>&1 || true)"
if ! grep -Fq 'DTD_PREFLIGHT_PYTHON is not executable' <<<"${invalid_python_output}"; then
  echo "Sandbox deployment must reject an invalid preflight interpreter before deployment" >&2
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
import tempfile

pattern = r"""/(?:assets/index|static/js/main)[^\"]*\.js"""
sample = '<script type="module" src="/assets/index-A1b2C3.js"></script>'
match = re.search(pattern, sample)
assert match and match.group(0) == "/assets/index-A1b2C3.js", match
script = pathlib.Path(os.environ["REPO_ROOT"]) / "scripts/deploy_sandbox_frontend.sh"
assert 'pathlib.Path(os.environ["REPO_ROOT"]) / "frontend/build/index.html"' in script.read_text()
with tempfile.TemporaryDirectory() as temporary_root:
    index_html = pathlib.Path(temporary_root) / "frontend/build/index.html"
    index_html.parent.mkdir(parents=True)
    index_html.write_text(sample)
    original_cwd = pathlib.Path.cwd()
    os.chdir(tempfile.gettempdir())
    try:
        built_html = (pathlib.Path(temporary_root) / "frontend/build/index.html").read_text()
    finally:
        os.chdir(original_cwd)
    built_match = re.search(pattern, built_html)
    assert built_match and built_match.group(0) == "/assets/index-A1b2C3.js", built_match
print("Sandbox frontend bundle parser: PASS")
PY

if ! grep -Fq -- '--update-headers="Content-Type=application/json"' "${repo_root}/scripts/setup_sandbox_ingestion.sh"; then
  echo "Scheduler provisioning must send JSON payloads to the FastAPI endpoint" >&2
  exit 1
fi

echo "SANDBOX_DEPLOY_CONTRACT=PASS"
