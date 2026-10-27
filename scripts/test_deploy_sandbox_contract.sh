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

for setting in ENABLE_TRAINER_BILLING_CHECKOUT=0 ENABLE_OPS_STRIPE_REFUNDS=0 OPS_SELF_HEALING_ENABLED=0; do
  if ! grep -Fq "${setting}" "${repo_root}/scripts/deploy_sandbox.sh"; then
    echo "Sandbox deployment must explicitly keep ${setting}" >&2
    exit 1
  fi
done

for setting in \
  'dtd-admin-pass:4' \
  'dtd-trainer-action-token-secret:2' \
  'STRIPE_KEY_UPDATED' \
  'STRIPE_LIVE_ANCHOR_AT' \
  '--no-traffic' \
  '--tag "${CANDIDATE_TAG}"' \
  'validate_ingestion_scheduler_paused'; do
  if ! grep -Fq -- "${setting}" "${repo_root}/scripts/deploy_sandbox.sh"; then
    echo "Sandbox deployment must explicitly enforce ${setting}" >&2
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

echo "🔍 Running comprehensive DF-006 behavioral lifecycle tests with fully intercepted mocks..."
REPO_ROOT="${repo_root}" python3 - <<'PY'
import json, os, subprocess, tempfile, sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
helper_script = repo_root / "scripts/deploy_sandbox.sh"

with tempfile.TemporaryDirectory() as test_dir:
    tpath = Path(test_dir)
    bin_dir = tpath / "bin"
    bin_dir.mkdir()
    
    mock_cli = tpath / "mock_cli.py"
    with open(mock_cli, "w") as f:
        f.write('''import json, os, sys, subprocess
state_file = os.environ["MOCK_STATE_FILE"]
with open(state_file) as f:
    state = json.load(f)

cmd = sys.argv[1]
args = sys.argv[2:]
state["trace"].append({"cmd": cmd, "args": args})

def get_arg(flag, default=""):
    for i, a in enumerate(args):
        if a == flag:
            return args[i+1] if i+1 < len(args) else default
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return default

def save():
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

scenario = state["scenario"]

if cmd == "gcloud":
    if args[:2] == ["meta", "list-files-for-upload"]:
        r = subprocess.run(["git", "-C", args[2], "ls-files"], capture_output=True, text=True)
        print(r.stdout.strip())
        save()
        sys.exit(0)

    if args[:4] == ["scheduler", "jobs", "describe", "dtd-trainer-ingest-cron"]:
        if scenario == "scheduler_missing":
            sys.stderr.write("Job not found\\n")
            save()
            sys.exit(5)
        if scenario == "scheduler_enabled":
            print("ENABLED")
            save()
            sys.exit(0)
        print("PAUSED")
        save()
        sys.exit(0)

    if args[:3] == ["run", "services", "describe"]:
        fmt = get_arg("--format")
        if fmt == "value(status.latestCreatedRevisionName)":
            print(state.get("latest_created", ""))
            save()
            sys.exit(0)
        if fmt == "value(status.url)":
            print(state.get("service_url", "https://dtd-api-dev.run.app"))
            save()
            sys.exit(0)
        
        traffic = [{"revisionName": state["serving"], "percent": 100}]
        if state.get("tag_revision"):
            tag_rev = state["tag_revision"]
            if scenario == "candidate_tag_mismatch":
                tag_rev = "foreign-mismatched-revision"
            traffic.append({"revisionName": tag_rev, "tag": "candidate", "url": "https://candidate---dtd-api-dev.run.app"})
        
        containers_env = []
        c_env = state.get("candidate_env") or state.get("existing_env", {})
        for k, v in c_env.items():
            containers_env.append({"name": k, "value": v})
        c_sec = state.get("candidate_secrets") or state.get("existing_secrets", {})
        for k, v in c_sec.items():
            if ":" in v:
                sec_name, sec_key = v.split(":", 1)
            else:
                sec_name, sec_key = v, "latest"
            containers_env.append({"name": k, "valueFrom": {"secretKeyRef": {"name": sec_name, "key": sec_key}}})

        body = {
            "status": {
                "url": state.get("service_url", "https://dtd-api-dev.run.app"),
                "latestCreatedRevisionName": state.get("latest_created", state["serving"]),
                "latestReadyRevisionName": state.get("latest_ready", state["serving"]),
                "traffic": traffic
            },
            "spec": {
                "template": {
                    "spec": {
                        "serviceAccountName": state.get("candidate_identity", "dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com"),
                        "containers": [{"env": containers_env}]
                    }
                }
            }
        }
        print(json.dumps(body))
        save()
        sys.exit(0)

    if args[:2] == ["run", "deploy"]:
        if scenario == "build_failure":
            sys.stderr.write("Cloud Run build failed\\n")
            save()
            sys.exit(9)
        suffix = get_arg("--revision-suffix")
        rev = "dtd-api-dev-" + suffix
        state["expected_revision"] = rev
        state["latest_created"] = rev
        state["latest_ready"] = rev
        state["tag_revision"] = rev
        
        env_arg = get_arg("--set-env-vars")
        state["candidate_env"] = dict([x.split("=", 1) for x in env_arg.split(",") if "=" in x])
        sec_arg = get_arg("--set-secrets")
        state["candidate_secrets"] = dict([x.split("=", 1) for x in sec_arg.split(",") if "=" in x])
        state["candidate_identity"] = get_arg("--service-account")

        if scenario == "wrong_candidate_metadata":
            state["candidate_env"]["DB_NAME"] = "other_synthetic_database"
            state["candidate_secrets"]["ADMIN_PASS"] = "synthetic-admin-other:99"
            state["candidate_identity"] = "other-synthetic-runtime@example.invalid"

        save()
        sys.exit(0)

    if args[:3] == ["run", "services", "update-traffic"]:
        if scenario == "promotion_failure" and "--to-revisions" in args:
            sys.stderr.write("Traffic update failed\\n")
            save()
            sys.exit(7)
        if "--to-revisions" in args:
            target = get_arg("--to-revisions")
            rev = target.split("=")[0]
            state["promoted_target"] = target
            state["serving"] = rev
        if "--remove-tags" in args:
            state["tag_revision"] = None
        save()
        sys.exit(0)

if cmd == "curl":
    url = args[-1]
    if "/api/health" in url and "candidate---" in url:
        state["health_checked_revision"] = state.get("tag_revision")
        if scenario == "candidate_health_failure":
            print('{"ok": true, "database": "unavailable"}')
            save()
            sys.exit(0)
        if scenario == "latest_race":
            state["latest_created"] = "dtd-api-dev-foreign-after-health"
            state["latest_ready"] = "dtd-api-dev-foreign-after-health"
        print('{"ok": true, "database": "available"}')
        save()
        sys.exit(0)
    elif "/api/health" in url:
        state["service_health_checked_revision"] = state["serving"]
        if scenario == "postpromotion_failure":
            print('{"ok": false, "database": "unavailable"}')
            save()
            sys.exit(0)
        print('{"ok": true, "database": "available"}')
        save()
        sys.exit(0)

sys.stderr.write(f"Unexpected invocation: {cmd} {args}\\n")
save()
sys.exit(1)
''')
    
    (bin_dir / "gcloud").write_text(f'#!/usr/bin/env bash\nexec python3 "{mock_cli}" gcloud "$@"\n')
    (bin_dir / "gcloud").chmod(0o755)
    (bin_dir / "curl").write_text(f'#!/usr/bin/env bash\nexec python3 "{mock_cli}" curl "$@"\n')
    (bin_dir / "curl").chmod(0o755)

    (bin_dir / "node").write_text('#!/usr/bin/env bash\nexit 0\n')
    (bin_dir / "node").chmod(0o755)

    def run_scenario(name, *, extra_env=None):
        case_dir = tpath / name
        case_dir.mkdir(exist_ok=True)
        state_file = case_dir / "state.json"
        
        initial = {
            "scenario": name,
            "serving": "dtd-api-dev-safe-serving-fixture",
            "latest_created": "dtd-api-dev-safe-serving-fixture",
            "latest_ready": "dtd-api-dev-safe-serving-fixture",
            "tag_revision": None,
            "service_url": "https://dtd-api-dev-625222421634.australia-southeast1.run.app",
            "trace": [],
            "existing_env": {
                "DB_NAME": "dtd_sandbox",
                "UNRELATED_SENTINEL": "preserve-me",
                "STRIPE_LIVE_ANCHOR_AT": "2026-11-01T00:00:00Z"
            },
            "existing_secrets": {
                "MONGO_URL": "dtd-mongo-url:7",
                "ADMIN_PASS": "dtd-admin-pass:4",
                "TRAINER_ACTION_TOKEN_SECRET": "dtd-trainer-action-token-secret:2",
                "EXTRA_SECRET": "extra:5"
            }
        }
        state_file.write_text(json.dumps(initial, indent=2))
        
        fake_python = case_dir / "mock_python"
        fake_python.write_text('#!/usr/bin/env bash\nif [ "${1:-}" = "-m" ] && [ "${2:-}" = "py_compile" ]; then exit 0; fi\nif [ "${FAIL_SUITE:-0}" = "1" ]; then exit 1; fi\nexit 0\n')
        fake_python.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["MOCK_STATE_FILE"] = str(state_file)
        env["DTD_PREFLIGHT_PYTHON"] = str(fake_python)
        if extra_env:
            env.update(extra_env)

        res = subprocess.run(["bash", str(helper_script)], cwd=repo_root, env=env, capture_output=True, text=True)
        with open(state_file) as f:
            st = json.load(f)
        return res, st

    # 1. Normal success
    r, s = run_scenario("normal")
    assert r.returncode == 0, f"normal failed (rc={r.returncode}):\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    assert s["serving"] == s["expected_revision"], f"Wrong serving: {s['serving']}"
    assert s["tag_revision"] is None, f"Tag candidate was not removed on success: {s['tag_revision']}"
    assert s["candidate_env"].get("UNRELATED_SENTINEL") == "preserve-me", f"Sentinel not preserved: {s['candidate_env']}"
    assert s["candidate_env"].get("STRIPE_LIVE_ANCHOR_AT") == "2026-11-01T00:00:00Z", f"Anchor not preserved: {s['candidate_env']}"
    assert s["candidate_secrets"].get("MONGO_URL") == "dtd-mongo-url:7", f"Mongo 7 not preserved: {s['candidate_secrets']}"
    assert s["candidate_secrets"].get("EXTRA_SECRET") == "extra:5", f"Extra secret not preserved: {s['candidate_secrets']}"
    assert s["candidate_secrets"].get("ADMIN_PASS") == "dtd-admin-pass:4", f"Admin pass not pinned: {s['candidate_secrets']}"
    assert s["candidate_secrets"].get("TRAINER_ACTION_TOKEN_SECRET") == "dtd-trainer-action-token-secret:2", f"Action token not pinned: {s['candidate_secrets']}"
    assert s["candidate_env"].get("DB_NAME") == "dtd_sandbox"
    assert s["candidate_env"].get("ENABLE_TRAINER_BILLING_CHECKOUT") == "0"
    print("  [DF006-A01/A02/A03] Scenario normal: PASS")

    # 2. Missing default interpreter
    r, s = run_scenario("default_missing_interpreter", extra_env={"DTD_PREFLIGHT_PYTHON": str(tpath / "nonexistent-python")})
    assert r.returncode == 64, f"Expected 64, got {r.returncode}"
    deploy_calls = sum(1 for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"])
    assert deploy_calls == 0, "Deploy was called despite missing interpreter"
    print("  [DF006-A04] Scenario default_missing_interpreter: PASS")

    # 3. Preflight suite failure
    r, s = run_scenario("suite_failure", extra_env={"FAIL_SUITE": "1"})
    assert r.returncode != 0, "Suite failure did not propagate"
    deploy_calls = sum(1 for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"])
    assert deploy_calls == 0, "Deploy was called despite suite failure"
    print("  [DF006-A04] Scenario suite_failure: PASS")

    # 4. Scheduler enabled
    r, s = run_scenario("scheduler_enabled")
    assert r.returncode == 64, f"Expected 64 for scheduler enabled, got {r.returncode}"
    deploy_calls = sum(1 for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"])
    assert deploy_calls == 0, "Deploy called despite scheduler enabled"
    print("  [DF006-A02] Scenario scheduler_enabled: PASS")

    # 5. Scheduler missing
    r, s = run_scenario("scheduler_missing")
    assert r.returncode == 64, f"Expected 64 for scheduler missing, got {r.returncode}"
    deploy_calls = sum(1 for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"])
    assert deploy_calls == 0, "Deploy called despite scheduler missing"
    print("  [DF006-A02] Scenario scheduler_missing: PASS")

    # 6. Build failure
    r, s = run_scenario("build_failure")
    assert r.returncode == 9
    assert s["serving"] == "dtd-api-dev-safe-serving-fixture"
    print("  [DF006-A03] Scenario build_failure: PASS")

    # 7. Candidate health failure
    r, s = run_scenario("candidate_health_failure")
    assert r.returncode != 0
    assert s["serving"] == "dtd-api-dev-safe-serving-fixture"
    assert s["tag_revision"] is None, "Tag was not cleaned up after candidate health failure"
    print("  [DF006-A03] Scenario candidate_health_failure: PASS")

    # 8. Candidate tag mismatch
    r, s = run_scenario("candidate_tag_mismatch")
    assert r.returncode != 0
    assert s["serving"] == "dtd-api-dev-safe-serving-fixture"
    assert s["tag_revision"] is None
    print("  [DF006-A01] Scenario candidate_tag_mismatch: PASS")

    # 9. Wrong candidate metadata
    r, s = run_scenario("wrong_candidate_metadata")
    assert r.returncode != 0
    assert s["serving"] == "dtd-api-dev-safe-serving-fixture"
    assert s["tag_revision"] is None
    print("  [DF006-A02] Scenario wrong_candidate_metadata: PASS")

    # 10. Latest race
    r, s = run_scenario("latest_race")
    assert r.returncode == 0
    assert s["serving"] == s["expected_revision"], f"Foreign revision promoted! serving={s['serving']}"
    assert s["tag_revision"] is None
    print("  [DF006-A01] Scenario latest_race: PASS")

    # 11. Post-promotion failure (traffic rollback)
    r, s = run_scenario("postpromotion_failure")
    assert r.returncode != 0
    assert s["serving"] == "dtd-api-dev-safe-serving-fixture", f"Rollback failed! serving={s['serving']}"
    assert s["tag_revision"] is None, "Tag not cleaned up after rollback"
    print("  [DF006-A03] Scenario postpromotion_failure: PASS")

    # 12. Candidate health probe omission mutation test
    mutated_script = tpath / "mutated_deploy_sandbox.sh"
    content = helper_script.read_text()
    mutated_content = content.replace(
        'CANDIDATE_HEALTH=$(curl --fail --silent --show-error --location --max-time 15 "${CANDIDATE_URL}/api/health")',
        'CANDIDATE_HEALTH=\'{"ok":true,"database":"available"}\''
    )
    assert mutated_content != content, "Failed to create mutation"
    mutated_script.write_text(mutated_content)
    
    case_dir = tpath / "mutation_test"
    case_dir.mkdir()
    state_file = case_dir / "state.json"
    state_file.write_text(json.dumps({
        "scenario": "candidate_health_failure",
        "serving": "dtd-api-dev-safe-serving-fixture",
        "latest_created": "dtd-api-dev-safe-serving-fixture",
        "latest_ready": "dtd-api-dev-safe-serving-fixture",
        "service_url": "https://dtd-api-dev.run.app",
        "tag_revision": None,
        "trace": []
    }))
    fake_python = case_dir / "mock_python"
    fake_python.write_text('#!/usr/bin/env bash\nexit 0\n')
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["MOCK_STATE_FILE"] = str(state_file)
    env["DTD_PREFLIGHT_PYTHON"] = str(fake_python)
    res_mut = subprocess.run(["bash", str(mutated_script)], cwd=repo_root, env=env, capture_output=True, text=True)
    assert res_mut.returncode == 0, f"Mutated script unexpectedly failed (rc={res_mut.returncode}): {res_mut.stderr}"
    print("  [DF006-A05] Scenario mutation_regression_detection: PASS (omitted health check detected)")

print("✅ All DF-006 behavioral lifecycle scenarios and regression detector passed.")
PY

echo "SANDBOX_DEPLOY_CONTRACT=PASS"

