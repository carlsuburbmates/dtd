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

for response in '{"ok":"True","database":"available"}' '{"ok":1,"database":"available"}' '{"ok":false,"database":"available"}' '{"ok":true,"database":"unavailable"}' 'not-json'; do
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
git -C "${source_test_root}" config commit.gpgsign false
mkdir -p "${source_test_root}/backend/tests" "${source_test_root}/bin"
printf 'committed source\n' >"${source_test_root}/backend/server.py"
printf '.env.*\ntests/\n' >"${source_test_root}/backend/.gcloudignore"
printf 'example only\n' >"${source_test_root}/backend/.env.example"
printf 'test fixture\n' >"${source_test_root}/backend/tests/test_fixture.py"
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
git -C "${source_test_root}" add .gitignore backend/.gcloudignore backend/server.py backend/.env.example backend/tests/test_fixture.py
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
printf 'staged source\n' >"${source_test_root}/backend/server.py"
git -C "${source_test_root}" add backend/server.py
staged_source_status=0
resolve_deploy_source_sha "${source_test_root}" >/dev/null 2>&1 || staged_source_status=$?
if [ "${staged_source_status}" -ne 64 ]; then
  echo "Sandbox deployment must reject staged backend changes" >&2
  exit 1
fi
git -C "${source_test_root}" reset --hard -q HEAD
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

# Direct preflight interpreter checks (both explicit invalid override and unset default)
set +e
invalid_python_output="$(DTD_PREFLIGHT_PYTHON="${repo_root}/does-not-exist" bash -c 'source "$1"; validate_preflight_interpreter' _ "${repo_root}/scripts/deploy_sandbox.sh" 2>&1)"
invalid_python_status=$?
set -e
if [ "${invalid_python_status}" -ne 64 ] || ! grep -Fq 'DTD_PREFLIGHT_PYTHON is not executable' <<<"${invalid_python_output}"; then
  echo "Sandbox preflight validation must reject an invalid interpreter with status 64" >&2
  exit 1
fi

set +e
empty_temp_dir="$(mktemp -d)"
default_missing_python_output="$(bash -c 'unset DTD_PREFLIGHT_PYTHON; cd "$2"; source "$1"; validate_preflight_interpreter' _ "${repo_root}/scripts/deploy_sandbox.sh" "${empty_temp_dir}" 2>&1)"
default_missing_python_status=$?
rm -rf "${empty_temp_dir}"
set -e
if [ "${default_missing_python_status}" -ne 64 ] || ! grep -Fq 'Sandbox preflight interpreter is missing or not executable' <<<"${default_missing_python_output}"; then
  echo "Sandbox preflight validation must reject missing default interpreter with status 64" >&2
  exit 1
fi

if grep -Eq '^[[:space:]]*bash .*setup_sandbox_ingestion\.sh' "${repo_root}/scripts/deploy_sandbox.sh"; then
  echo "Deployment must not silently invoke scheduler/IAM provisioning" >&2
  exit 1
fi

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

echo "Running DF-006 lifecycle tests with closed local provider mocks..."
REPO_ROOT="${repo_root}" python3 - <<'PY'
import copy
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
helper_source = (repo_root / "scripts/deploy_sandbox.sh").read_text()
identity = "dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com"
image = "australia-southeast1-docker.pkg.dev/dogtrainersdirectory-dev/cloud-run-source-deploy/dtd-api-dev@sha256:" + "a" * 64

# This process never dispatches an unrecognised call to a real provider or network.
mock_source = r'''import copy, json, os, re, sys
from pathlib import Path
p = Path(os.environ["MOCK_STATE_FILE"])
s = json.loads(p.read_text())
tool, args = sys.argv[1], sys.argv[2:]
scenario = s["scenario"]
s["trace"].append({"tool": tool, "args": args})
def fixture_error(kind, value, traceback):
    s["mock_error"] = str(value)
    p.write_text(json.dumps(s))
    sys.__excepthook__(kind, value, traceback)
sys.excepthook = fixture_error
def done(value=None, code=0):
    p.write_text(json.dumps(s))
    if value is not None:
        print(value if isinstance(value, str) else json.dumps(value))
    raise SystemExit(code)
def arg(flag):
    for i, value in enumerate(args):
        if value == flag:
            return args[i + 1]
        if value.startswith(flag + "="):
            return value.split("=", 1)[1]
    return ""
def parse_values(value):
    if value.startswith("^"):
        delimiter, value = value[1:].split("^", 1)
    else:
        delimiter = ","
    entries = value.split(delimiter)
    if any("=" not in entry for entry in entries):
        done("Invalid dictionary argument", 2)
    return dict(entry.split("=", 1) for entry in entries)
def spec(env, secrets):
    return {"serviceAccountName": s["identity"], "containers": [{"image": s["image"], "env":
        [{"name": key, "value": value} for key, value in sorted(env.items())] +
        [{"name": key, "valueFrom": {"secretKeyRef": {"name": value.rsplit(":", 1)[0], "key": value.rsplit(":", 1)[1]}}}
         for key, value in sorted(secrets.items())]}]}
def revision(name, env, secrets):
    return {"metadata": {"name": name, "labels": {"serving.knative.dev/service": "dtd-api-dev"}},
        "spec": spec(env, secrets), "status": {"imageDigest": s["image"], "conditions": [{"type": "Ready", "status": "True"}]}}
def service():
    env = s.get("candidate_env", s["baseline_env"])
    secrets = s.get("candidate_secrets", s["baseline_secrets"])
    traffic = copy.deepcopy(s["routing"])
    for tag, owner in s["tags"].items():
        traffic.append({"tag": tag, "revisionName": owner, "url": "https://" + tag + "---fixture.example.invalid"})
    latest = s.get("candidate", s["prior"])
    if scenario == "foreign_latest" and s.get("candidate_health"):
        latest = "dtd-api-dev-foreign-created"
    return {"metadata": {"name": "dtd-api-dev", "generation": 1},
        "spec": {"template": {"metadata": {"name": latest}, "spec": spec(env, secrets)}},
        "status": {"url": s["url"], "latestCreatedRevisionName": latest,
            "latestReadyRevisionName": latest, "traffic": traffic, "conditions": [{"type": "Ready", "status": "True"}]}}
if tool == "node":
    done()
if tool == "suite":
    done(code=1 if scenario == "suite_failure" else 0)
if tool == "gcloud":
    if args[:2] == ["meta", "list-files-for-upload"]:
        # These are exactly the synthetic fixture's deployable files. The fixture's
        # tracked .env.example and tests are excluded by its .gcloudignore.
        done(".gcloudignore\nserver.py\nworker.py\nservices/example.py")
    if args[:4] == ["scheduler", "jobs", "describe", "dtd-trainer-ingest-cron"]:
        if scenario in ["scheduler_missing", "scheduler_read_error"]:
            done("Synthetic Scheduler read failure", 5)
        done("ENABLED" if scenario == "scheduler_enabled" else "PAUSED")
    if args[:3] == ["run", "services", "describe"]:
        s["service_reads"] = s.get("service_reads", 0) + 1
        if scenario == "baseline_config_drift" and s["service_reads"] == 2:
            s["baseline_env"]["UNRELATED_SENTINEL"] = "concurrent-configuration-change"
        if scenario == "baseline_read_error" and "candidate" not in s:
            done("Synthetic baseline read failure", 6)
        if s.get("service_health"):
            s["after_service_reads"] = s.get("after_service_reads", 0) + 1
            if scenario == "recovery_read_error" or (scenario == "cleanup_read_error" and s["after_service_reads"] >= 2):
                done("Synthetic state read failure", 6)
        if s.get("promotion_failed") and scenario == "promotion_unknown":
            done("Synthetic state read failure", 6)
        if s.get("candidate_health") and not s.get("promoted"):
            if scenario == "prepromotion_invalid_json":
                done("invalid-json")
            if scenario == "prepromotion_empty_routes":
                data = service(); data["status"]["traffic"] = []
                done(data)
        if arg("--format") == "value(status.url)":
            done(s["url"])
        data = service()
        if scenario == "baseline_missing_template" and "candidate" not in s:
            data["spec"] = {}
        if scenario == "baseline_missing_container" and "candidate" not in s:
            data["spec"]["template"]["spec"]["containers"] = []
        if scenario == "missing_tag_url":
            for route in data["status"]["traffic"]:
                if route.get("tag") == s.get("candidate_tag"):
                    route.pop("url", None)
        s.setdefault("service_snapshots", []).append(copy.deepcopy(data["status"]["traffic"]))
        done(data)
    if args[:2] == ["run", "deploy"]:
        if scenario == "build_failure":
            done("Synthetic build failure", 9)
        assert "--no-traffic" in args, "Candidate must be created without traffic"
        assert arg("--format") == "json", "Capture deploy result for image/revision evidence"
        s["candidate"] = "dtd-api-dev-" + arg("--revision-suffix")
        s["candidate_tag"] = arg("--tag")
        assert s["candidate_tag"] and s["candidate_tag"] != "candidate", "Require an invocation-owned tag"
        s["tags"][s["candidate_tag"]] = s["candidate"]
        s["candidate_env"] = parse_values(arg("--set-env-vars"))
        s["candidate_secrets"] = parse_values(arg("--set-secrets"))
        assert arg("--service-account") == s["identity"]
        result = service()
        if scenario == "unpinned_deploy_image":
            result["spec"]["template"]["spec"]["containers"][0]["image"] = "synthetic:latest"
        if scenario == "wrong_deploy_revision":
            result["spec"]["template"]["metadata"]["name"] = "dtd-api-dev-foreign"
        # Actual immutable candidate metadata can diverge after captured result.
        if scenario == "candidate_preservation_loss":
            s["candidate_env"].pop("UNRELATED_SENTINEL")
        if scenario == "candidate_secret_loss":
            s["candidate_secrets"].pop("EXTRA_SECRET")
        done(result)
    if args[:3] == ["run", "revisions", "describe"]:
        name = args[3]
        if name == s.get("candidate"):
            if scenario == "missing_metadata":
                done({})
            data = revision(name, s["candidate_env"], s["candidate_secrets"])
            if scenario == "candidate_unready":
                data["status"]["conditions"][0]["status"] = "False"
            if scenario == "wrong_revision_name":
                data["metadata"]["name"] = "dtd-api-dev-foreign"
            if scenario == "wrong_identity":
                data["spec"]["serviceAccountName"] = "foreign-runtime@example.invalid"
            if scenario == "wrong_image":
                data["spec"]["containers"][0]["image"] = "foreign@sha256:" + "b" * 64
                data["status"]["imageDigest"] = "foreign@sha256:" + "b" * 64
            if scenario == "wrong_image_digest":
                data["status"]["imageDigest"] = "foreign@sha256:" + "b" * 64
            if scenario == "wrong_db":
                next(e for e in data["spec"]["containers"][0]["env"] if e["name"] == "DB_NAME")["value"] = "other_database"
            if scenario.startswith("wrong_flag_"):
                key = scenario[len("wrong_flag_"):]
                next(e for e in data["spec"]["containers"][0]["env"] if e["name"] == key)["value"] = "1"
            if scenario in ["wrong_admin_pin", "wrong_action_pin"]:
                key = "ADMIN_PASS" if scenario == "wrong_admin_pin" else "TRAINER_ACTION_TOKEN_SECRET"
                next(e for e in data["spec"]["containers"][0]["env"] if e["name"] == key)["valueFrom"]["secretKeyRef"]["key"] = "99"
            if scenario == "tag_retarget_before_health":
                s["tags"][s["candidate_tag"]] = "foreign-tag-owner"
            done(data)
        assert name == s["prior"], "Unknown revision read"
        data = revision(name, s["prior_env"], s["baseline_secrets"])
        if scenario == "unsafe_prior":
            next(e for e in data["spec"]["containers"][0]["env"] if e["name"] == "ADMIN_PASS")["valueFrom"]["secretKeyRef"]["key"] = "1"
        done(data)
    if args[:3] == ["run", "services", "update-traffic"]:
        if arg("--to-revisions"):
            target = arg("--to-revisions")
            if scenario == "promotion_failure" and not s.get("promoted"):
                done("Synthetic promotion failure", 7)
            s.setdefault("traffic_writes", []).append({"before": copy.deepcopy(s["routing"]), "target": target})
            name, percent = target.rsplit("=", 1)
            assert int(percent) == 100
            s["routing"] = [{"revisionName": name, "percent": 100}]
            s["promoted"] = True
            if scenario in ["promotion_response_lost", "promotion_unknown"]:
                s["promotion_failed"] = True
                done("Synthetic response lost after applying traffic", 7)
        if arg("--remove-tags"):
            tag = arg("--remove-tags")
            if scenario == "cleanup_failure":
                done("Synthetic cleanup failure", 7)
            assert tag == s.get("candidate_tag"), "Only invocation-owned tag may be removed"
            s.setdefault("removed_tags", []).append({"tag": tag, "owner": s["tags"].pop(tag, None)})
        done()
if tool == "curl":
    url = args[-1]
    tag_prefix = "https://" + s.get("candidate_tag", "missing") + "---"
    if url.startswith(tag_prefix):
        s["candidate_health"] = s["tags"].get(s["candidate_tag"])
        if scenario == "candidate_health_failure":
            done({"ok": False, "database": "unavailable"})
        if scenario == "candidate_http_failure":
            done("Synthetic candidate HTTP failure", 22)
        if scenario == "tag_retarget_after_health":
            s["tags"][s["candidate_tag"]] = "foreign-tag-owner"
        if scenario == "traffic_changed_after_health":
            s["routing"] = [{"revisionName": "foreign-operator", "percent": 100}]
        if scenario == "prepromotion_split":
            s["routing"] = [{"revisionName": s["prior"], "percent": 50}, {"revisionName": "foreign-operator", "percent": 50}]
        done({"ok": True, "database": "available"})
    assert url == s["url"] + "/api/health", "Unknown URL must never reach a real network"
    s["service_health"] = True
    if scenario == "concurrent_posthealth_failure":
        s["routing"] = [{"revisionName": "foreign-operator", "percent": 100}]
    if scenario == "recovery_split":
        s["routing"] = [{"revisionName": s["candidate"], "percent": 50}, {"revisionName": "foreign-operator", "percent": 50}]
    if scenario == "tag_retarget_on_success":
        s["tags"][s["candidate_tag"]] = "foreign-tag-owner"
    if scenario in ["postpromotion_failure", "unsafe_prior", "concurrent_posthealth_failure", "recovery_read_error", "recovery_split"] and s["routing"] != [{"revisionName": s["prior"], "percent": 100}]:
        done({"ok": False, "database": "unavailable"})
    done({"ok": True, "database": "available"})
s["unexpected"] = {"tool": tool, "args": args}
done("Unexpected closed mock invocation", 90)
'''

with tempfile.TemporaryDirectory(prefix="dtd-deploy-contract-") as temporary:
    base = Path(temporary)
    fixture = base / "repo"
    fixture.mkdir()
    (fixture / "backend/services").mkdir(parents=True)
    (fixture / "backend/tests").mkdir()
    (fixture / "scripts").mkdir()
    for path in ["server.py", "worker.py", "services/example.py", "tests/test_fixture.py"]:
        (fixture / "backend" / path).write_text("# synthetic fixture\n")
    (fixture / "backend/.env.example").write_text("EXAMPLE=placeholder\n")
    (fixture / "backend/.gcloudignore").write_text(".env.*\ntests/\n__pycache__/\n*.py[cod]\n")
    helper = fixture / "scripts/deploy_sandbox.sh"
    helper.write_text(helper_source)
    for command in [
        ["git", "init", "-q"], ["git", "config", "user.name", "DTD deployment contract"],
        ["git", "config", "user.email", "sandbox-contract@example.invalid"],
        ["git", "config", "commit.gpgsign", "false"], ["git", "add", "."], ["git", "commit", "-qm", "fixture"]
    ]:
        subprocess.run(command, cwd=fixture, check=True, capture_output=True)
    mock = base / "mock_cli.py"
    mock.write_text(mock_source)
    bin_dir = base / "bin"
    bin_dir.mkdir()
    for tool in ["gcloud", "curl", "node"]:
        stub = bin_dir / tool
        stub.write_text(f'#!/bin/bash\nexec /usr/bin/python3 "{mock}" {tool} "$@"\n')
        stub.chmod(0o755)
    # Keep compilation local and deterministic while executing all actual parser code.
    python_stub = bin_dir / "python3"
    python_stub.write_text('#!/bin/bash\nif [ "${1:-}" = "-m" ] && [ "${2:-}" = "py_compile" ]; then exit 0; fi\nexec /usr/bin/python3 "$@"\n')
    python_stub.chmod(0o755)
    count = 0

    def run(name, helper_override=None, suite_failure=False, missing_default=False, invalid_override=False):
        case = base / (name + "-" + str(len(list(base.iterdir()))))
        case.mkdir()
        state_path = case / "state.json"
        env_values = {
            "DB_NAME": "dtd_sandbox", "UNRELATED_SENTINEL": "preserve-me",
            "STRIPE_LIVE_ANCHOR_AT": "2026-11-01T00:00:00Z", "STRIPE_KEY_UPDATED": "2",
            "ENABLE_TRAINER_BILLING_CHECKOUT": "0", "ENABLE_OPS_STRIPE_REFUNDS": "0",
            "OPS_SELF_HEALING_ENABLED": "0", "SENTRY_ENVIRONMENT": "staging",
            "DISABLE_AUTONOMY": "1", "ENABLE_STARTUP_SEEDS": "0", "AUTONOMY_LOOP_OWNER": "none",
            "CLOUD_SCHEDULER_OIDC_SERVICE_ACCOUNT": identity,
            "CLOUD_SCHEDULER_OIDC_AUDIENCE": "https://dtd-api-dev-625222421634.australia-southeast1.run.app",
        }
        if name == "comma_env_preservation":
            env_values["EXTRA_LIST"] = "alpha,beta;;gamma@@delta"
        state = {"scenario": "suite_failure" if suite_failure else name,
            "identity": identity, "image": image, "url": "https://dtd-api-dev-625222421634.australia-southeast1.run.app",
            "prior": "dtd-api-dev-safe-prior", "routing": [{"revisionName": "dtd-api-dev-safe-prior", "percent": 100}],
            "tags": {"unrelated": "dtd-api-dev-other-tag"}, "trace": [], "baseline_env": env_values,
            "prior_env": dict(env_values),
            "baseline_secrets": {"ADMIN_PASS": "dtd-admin-pass:4", "TRAINER_ACTION_TOKEN_SECRET": "dtd-trainer-action-token-secret:2", "MONGO_URL": "dtd-mongo-url:7", "EXTRA_SECRET": "synthetic-extra:5"}}
        if name == "unsafe_prior":
            state["baseline_secrets"]["ADMIN_PASS"] = "dtd-admin-pass:1"
        if name == "split_traffic_baseline":
            state["routing"] = [{"revisionName": "rev-a", "percent": 50}, {"revisionName": "rev-b", "percent": 50}]
        state_path.write_text(json.dumps(state))
        suite = case / "suite"
        suite.write_text(f'#!/bin/bash\nexec /usr/bin/python3 "{mock}" suite "$@"\n')
        suite.chmod(0o755)
        environment = {"PATH": str(bin_dir) + ":/usr/bin:/bin:/usr/sbin:/sbin", "MOCK_STATE_FILE": str(state_path), "LC_ALL": "C"}
        if not missing_default:
            environment["DTD_PREFLIGHT_PYTHON"] = str(case / "missing" if invalid_override else suite)
        result = subprocess.run(["bash", str(helper_override or helper)], cwd=fixture, env=environment, capture_output=True, text=True, timeout=30)
        final = json.loads(state_path.read_text())
        assert "unexpected" not in final, final.get("unexpected")
        assert "mock_error" not in final, final.get("mock_error")
        assert final["tags"].get("unrelated") == "dtd-api-dev-other-tag", "Unrelated tags must be retained"
        return result, final

    def passing(name):
        process, state = run(name)
        assert process.returncode == 0, (name, process.returncode, process.stdout, process.stderr)
        assert state["routing"] == [{"revisionName": state["candidate"], "percent": 100}], name
        assert state.get("candidate_health") == state["candidate"], "Probe must verify the promoted revision"
        assert state["candidate_tag"] not in state["tags"], "Owned temporary tag must be removed"
        assert state["candidate_env"]["UNRELATED_SENTINEL"] == "preserve-me"
        assert state["candidate_env"]["STRIPE_LIVE_ANCHOR_AT"] == "2026-11-01T00:00:00Z"
        assert state["candidate_secrets"]["MONGO_URL"] == "dtd-mongo-url:7"
        assert state["candidate_secrets"]["EXTRA_SECRET"] == "synthetic-extra:5"
        for flag in ["ENABLE_TRAINER_BILLING_CHECKOUT", "ENABLE_OPS_STRIPE_REFUNDS", "OPS_SELF_HEALING_ENABLED"]:
            assert state["candidate_env"][flag] == "0"
        tools = [entry["tool"] for entry in state["trace"]]
        assert "suite" in tools
        deploy = next(i for i, e in enumerate(state["trace"]) if e["tool"] == "gcloud" and e["args"][:2] == ["run", "deploy"])
        assert tools.index("suite") < deploy, "Mandatory suite must precede deployment"
        return state

    for scenario in ["normal", "foreign_latest", "comma_env_preservation"]:
        state = passing(scenario)
        if scenario == "comma_env_preservation":
            assert state["candidate_env"]["EXTRA_LIST"] == "alpha,beta;;gamma@@delta"
        count += 1
        print("  PASS", scenario, flush=True)

    # Candidate faults are independent: one bad field cannot mask another missing check.
    candidate_faults = ["missing_tag_url", "wrong_image_digest", "unpinned_deploy_image", "wrong_deploy_revision", "missing_metadata", "candidate_unready", "wrong_revision_name", "wrong_identity", "wrong_image", "wrong_db", "wrong_admin_pin", "wrong_action_pin", "candidate_preservation_loss", "candidate_secret_loss", "candidate_health_failure", "candidate_http_failure", "tag_retarget_before_health", "tag_retarget_after_health"]
    candidate_faults += ["wrong_flag_" + flag for flag in ["ENABLE_TRAINER_BILLING_CHECKOUT", "ENABLE_OPS_STRIPE_REFUNDS", "OPS_SELF_HEALING_ENABLED"]]
    for scenario in candidate_faults:
        process, state = run(scenario)
        assert process.returncode != 0, (scenario, process.stdout, process.stderr)
        assert not state.get("traffic_writes"), (scenario, "must not promote")
        assert state["routing"] == [{"revisionName": state["prior"], "percent": 100}]
        assert not any(entry["owner"] == "foreign-tag-owner" for entry in state.get("removed_tags", [])), "Preserve foreign tag"
        count += 1
        print("  PASS", scenario, flush=True)

    for scenario in ["scheduler_enabled", "scheduler_missing", "scheduler_read_error", "baseline_read_error", "baseline_missing_template", "baseline_missing_container", "baseline_config_drift", "split_traffic_baseline"]:
        process, state = run(scenario)
        assert process.returncode != 0, (scenario, process.stderr)
        assert not any(entry["tool"] == "gcloud" and entry["args"][:2] == ["run", "deploy"] for entry in state["trace"]), scenario
        count += 1
        print("  PASS", scenario, flush=True)

    for name, options in [("missing_default", {"missing_default": True}), ("invalid_override", {"invalid_override": True}), ("suite_failure", {"suite_failure": True})]:
        process, state = run(name, **options)
        assert process.returncode != 0
        assert not any(entry["tool"] == "gcloud" and entry["args"][:2] == ["run", "deploy"] for entry in state["trace"])
        count += 1
        print("  PASS", name, flush=True)

    for scenario in ["traffic_changed_after_health", "prepromotion_split", "prepromotion_empty_routes", "prepromotion_invalid_json"]:
        process, state = run(scenario)
        assert process.returncode != 0, (scenario, process.stderr)
        assert not state.get("traffic_writes"), (scenario, "must preserve concurrent/unknown traffic")
        count += 1
        print("  PASS", scenario, flush=True)

    for scenario in ["build_failure", "promotion_failure"]:
        process, state = run(scenario)
        assert process.returncode != 0
        assert not state.get("traffic_writes")
        assert state["routing"] == [{"revisionName": state["prior"], "percent": 100}]
        count += 1
        print("  PASS", scenario, flush=True)

    for scenario in ["postpromotion_failure", "promotion_response_lost"]:
        process, state = run(scenario)
        assert process.returncode != 0, (scenario, process.stderr)
        assert state["routing"] == [{"revisionName": state["prior"], "percent": 100}], (scenario, "must recover safely")
        assert len(state.get("traffic_writes", [])) == 2
        assert state["candidate_tag"] not in state["tags"]
        count += 1
        print("  PASS", scenario, flush=True)

    for scenario in ["unsafe_prior", "concurrent_posthealth_failure", "recovery_split", "recovery_read_error", "promotion_unknown"]:
        process, state = run(scenario)
        assert process.returncode != 0
        assert len(state.get("traffic_writes", [])) == 1, (scenario, "must not blindly roll back")
        assert re.search("guarded|unknown|manual|operator", process.stderr, re.I), (scenario, "must report recovery disposition")
        count += 1
        print("  PASS", scenario, flush=True)

    for scenario in ["cleanup_failure", "cleanup_read_error"]:
        process, state = run(scenario)
        assert process.returncode != 0, (scenario, "must report incomplete cleanup")
        assert state["candidate_tag"] in state["tags"]
        count += 1
        print("  PASS", scenario, flush=True)

    process, state = run("tag_retarget_on_success")
    assert state["tags"].get(state["candidate_tag"]) == "foreign-tag-owner"
    assert not any(entry["owner"] == "foreign-tag-owner" for entry in state.get("removed_tags", []))
    count += 1
    print("  PASS tag_retarget_on_success", flush=True)

    # Reuse a real negative acceptance assertion against a controlled health omission.
    def rejects_unhealthy_candidate(process, state):
        assert process.returncode != 0 and not state.get("traffic_writes"), "Unhealthy candidate was promoted"

    process, state = run("candidate_health_failure")
    rejects_unhealthy_candidate(process, state)
    pattern = r'(?m)^(\s*)CANDIDATE_HEALTH=\$\(curl[^\n]+\)\n\s*validate_health_response "\$\{CANDIDATE_HEALTH\}"'
    mutated, replacements = re.subn(pattern, lambda match: match[1] + """CANDIDATE_HEALTH='{"ok":true,"database":"available"}'""", helper_source, count=1)
    assert replacements == 1, "Controlled health mutation must change exactly one probe"
    mutant = base / "mutated-deploy_sandbox.sh"
    mutant.write_text(mutated)
    process, state = run("candidate_health_failure", helper_override=mutant)
    try:
        rejects_unhealthy_candidate(process, state)
    except AssertionError:
        assert state.get("traffic_writes"), "Mutation proof must reach the unsafe promotion"
    else:
        raise AssertionError("Maintained unhealthy-candidate assertion failed to detect the controlled regression")
    count += 1
    print("  PASS mutation_regression_detection: unhealthy-candidate assertion rejects health omission")
    print("DF006_BEHAVIORAL_CASES=" + str(count))
PY

echo "SANDBOX_DEPLOY_CONTRACT=PASS"
