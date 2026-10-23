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

if ! grep -Fq -- '--revision-suffix "${REVISION_SUFFIX}"' "${repo_root}/scripts/deploy_sandbox.sh"; then
  echo "Sandbox revisions must carry their committed source SHA suffix" >&2
  exit 1
fi

source_test_root="$(mktemp -d)"
trap 'rm -rf "${source_test_root}"' EXIT
git -C "${source_test_root}" init -q
git -C "${source_test_root}" config user.name "DTD sandbox contract test"
git -C "${source_test_root}" config user.email "sandbox-contract@example.invalid"
mkdir -p "${source_test_root}/backend" "${source_test_root}/bin"
printf 'committed source\n' >"${source_test_root}/backend/server.py"
printf '.gcloudignore\n' >"${source_test_root}/backend/.gcloudignore"
printf 'backend/credentials.json\n' >"${source_test_root}/.gitignore"
cat >"${source_test_root}/bin/gcloud" <<'MOCK_GCLOUD'
#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 3 ] || [ "$1" != meta ] || [ "$2" != list-files-for-upload ]; then
  echo "unexpected gcloud invocation" >&2
  exit 64
fi
if [ "${MOCK_GCLOUD_FAIL:-0}" = 1 ]; then
  exit 2
fi
cat "${UPLOAD_MANIFEST}"
MOCK_GCLOUD
chmod +x "${source_test_root}/bin/gcloud"
export UPLOAD_MANIFEST="${source_test_root}/upload-manifest.txt"
export PATH="${source_test_root}/bin:${PATH}"
printf '.gcloudignore\nserver.py\n' >"${UPLOAD_MANIFEST}"
git -C "${source_test_root}" add .gitignore backend/.gcloudignore backend/server.py
git -C "${source_test_root}" commit -q -m "fixture source"
source_sha="$(resolve_deploy_source_sha "${source_test_root}")"
if [ "${source_sha}" != "$(git -C "${source_test_root}" rev-parse HEAD)" ]; then
  echo "Sandbox deploy source resolver did not return HEAD" >&2
  exit 1
fi
export MOCK_GCLOUD_FAIL=1
set +e
gcloud_failure_status=0
resolve_deploy_source_sha "${source_test_root}" >/dev/null 2>&1 || gcloud_failure_status=$?
set -e
unset MOCK_GCLOUD_FAIL
if [ "${gcloud_failure_status}" -ne 64 ]; then
  echo "Sandbox deployment must fail closed when Cloud Run upload inspection fails" >&2
  exit 1
fi
printf '\n' >"${UPLOAD_MANIFEST}"
set +e
empty_manifest_status=0
resolve_deploy_source_sha "${source_test_root}" >/dev/null 2>&1 || empty_manifest_status=$?
set -e
if [ "${empty_manifest_status}" -ne 64 ]; then
  echo "Sandbox deployment must reject an empty Cloud Run upload manifest" >&2
  exit 1
fi
printf '.gcloudignore\nserver.py\n' >"${UPLOAD_MANIFEST}"
printf 'uncommitted source\n' >"${source_test_root}/backend/server.py"
set +e
dirty_source_status=0
resolve_deploy_source_sha "${source_test_root}" >/dev/null 2>&1 || dirty_source_status=$?
set -e
if [ "${dirty_source_status}" -ne 64 ]; then
  echo "Sandbox deployment must reject a modified backend source tree" >&2
  exit 1
fi
git -C "${source_test_root}" checkout -- backend/server.py
printf 'credential material\n' >"${source_test_root}/backend/credentials.json"
printf '.gcloudignore\ncredentials.json\nserver.py\n' >"${UPLOAD_MANIFEST}"
set +e
ignored_source_status=0
resolve_deploy_source_sha "${source_test_root}" >/dev/null 2>&1 || ignored_source_status=$?
set -e
if [ "${ignored_source_status}" -ne 64 ]; then
  echo "Sandbox deployment must reject ignored backend files included by source upload" >&2
  exit 1
fi
rm "${source_test_root}/backend/credentials.json"
printf 'untracked source\n' >"${source_test_root}/backend/untracked.py"
printf '.gcloudignore\nserver.py\nuntracked.py\n' >"${UPLOAD_MANIFEST}"
set +e
untracked_source_status=0
resolve_deploy_source_sha "${source_test_root}" >/dev/null 2>&1 || untracked_source_status=$?
set -e
if [ "${untracked_source_status}" -ne 64 ]; then
  echo "Sandbox deployment must reject untracked backend source" >&2
  exit 1
fi
rm -rf "${source_test_root}"
trap - EXIT

set +e
invalid_python_output="$(DTD_PREFLIGHT_PYTHON="${repo_root}/does-not-exist" bash -c 'source "$1"; validate_preflight_interpreter' _ "${repo_root}/scripts/deploy_sandbox.sh" 2>&1)"
invalid_python_status=$?
set -e
if [ "${invalid_python_status}" -ne 64 ] || ! grep -Fq 'DTD_PREFLIGHT_PYTHON is not executable' <<<"${invalid_python_output}"; then
  echo "Sandbox preflight validation must reject an invalid interpreter with status 64" >&2
  exit 1
fi

if grep -Eq '^[[:space:]]*bash .*setup_sandbox_ingestion\.sh' "${repo_root}/scripts/deploy_sandbox.sh"; then
  echo "Deployment must not silently invoke scheduler/IAM provisioning" >&2
  exit 1
fi

for setting in ENABLE_TRAINER_BILLING_CHECKOUT=1 OPS_SELF_HEALING_ENABLED=1; do
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
