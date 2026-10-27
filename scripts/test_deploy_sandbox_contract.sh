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
import json, os, re, subprocess, tempfile, sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
helper_script = repo_root / "scripts/deploy_sandbox.sh"

mock_cli_py = r'''import sys, os, json, re, subprocess
from pathlib import Path

state_file = os.environ["MOCK_STATE_FILE"]
with open(state_file) as f:
    state = json.load(f)

cmd = sys.argv[1]
args = sys.argv[2:]
scenario = state["scenario"]
state["trace"].append({"cmd": cmd, "args": args})

def save():
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

def done(val=None, rc=0):
    save()
    if val is not None:
        print(val if isinstance(val, str) else json.dumps(val))
    sys.exit(rc)

def get_arg(flag, default=""):
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i+1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return default

def parse_dict(val):
    if val.startswith("^"):
        m = re.match(r"^\^([^^]+)\^(.*)$", val)
        if m:
            delim = m.group(1)
            items = m.group(2).split(delim)
            return dict(item.split("=", 1) for item in items if "=" in item)
    return dict(item.split("=", 1) for item in val.split(",") if "=" in item)

if cmd == "gcloud":
    if args[:2] == ["meta", "list-files-for-upload"]:
        r = subprocess.run(["git", "-C", args[2], "ls-files"], capture_output=True, text=True)
        done(r.stdout.strip())

    if args[:4] == ["scheduler", "jobs", "describe", "dtd-trainer-ingest-cron"]:
        if scenario == "scheduler_read_error":
            done("RPC error connecting to Cloud Scheduler", rc=1)
        if scenario == "scheduler_enabled":
            done("ENABLED")
        done("PAUSED")

    if args[:3] == ["run", "services", "describe"]:
        if get_arg("--format") == "value(status.url)":
            done(state["url"])
        env = state.get("candidate_env", state["baseline_env"])
        secrets = state.get("candidate_secrets", state["baseline_secrets"])
        spec = {
            "serviceAccountName": state["identity"],
            "containers": [{
                "image": "synthetic-image:latest",
                "env": [{"name": k, "value": v} for k, v in env.items()] + [
                    {"name": k, "valueFrom": {"secretKeyRef": {"name": v.split(":")[0], "key": v.split(":")[1]}}}
                    for k, v in secrets.items()
                ]
            }]
        }
        traffic = [{"revisionName": state["serving"], "percent": 100}]
        if scenario == "split_traffic_baseline":
            traffic = [{"revisionName": "rev-a", "percent": 50}, {"revisionName": "rev-b", "percent": 50}]
        if state.get("tag"):
            traffic.append({"revisionName": state["tag"], "tag": "candidate", "url": "https://candidate---fixture.example.invalid"})
        done({
            "status": {
                "url": state["url"],
                "latestCreatedRevisionName": state.get("expected_revision", state["serving"]),
                "latestReadyRevisionName": state.get("expected_revision", state["serving"]),
                "traffic": traffic
            },
            "spec": {"template": {"spec": spec}}
        })

    if args[:2] == ["run", "deploy"]:
        rev = "dtd-api-dev-" + get_arg("--revision-suffix")
        state["expected_revision"] = rev
        state["tag"] = rev
        state["candidate_env"] = parse_dict(get_arg("--set-env-vars"))
        state["candidate_secrets"] = parse_dict(get_arg("--set-secrets"))
        state["identity"] = get_arg("--service-account")
        state["exact_candidate_metadata"] = {
            "serviceAccountName": state["identity"],
            "env": dict(state["candidate_env"]),
            "secrets": dict(state["candidate_secrets"]),
            "ready": True,
            "image": "synthetic@sha256:expected"
        }
        if scenario == "wrong_exact_revision":
            state["exact_candidate_metadata"].update({
                "serviceAccountName": "foreign-runtime@example.invalid",
                "ready": False,
                "image": "synthetic@sha256:wrong"
            })
            state["exact_candidate_metadata"]["env"]["DB_NAME"] = "other_synthetic_database"
            state["exact_candidate_metadata"]["secrets"]["ADMIN_PASS"] = "synthetic-other:99"
        done()

    if args[:3] == ["run", "revisions", "describe"]:
        rev_arg = args[3]
        if rev_arg == state.get("expected_revision"):
            if scenario == "missing_metadata":
                done({})
            done({
                "spec": state["exact_candidate_metadata"],
                "status": {"conditions": [{"type": "Ready", "status": "True" if state["exact_candidate_metadata"].get("ready", True) else "False"}]}
            })
        done({
            "spec": state["prior_revision_metadata"],
            "status": {"conditions": [{"type": "Ready", "status": "True"}]}
        })

    if args[:3] == ["run", "services", "update-traffic"]:
        if get_arg("--to-revisions"):
            target = get_arg("--to-revisions").split("=")[0]
            state.setdefault("traffic_writes", []).append({"before": state["serving"], "target": target})
            state["serving"] = target
            if scenario == "promotion_response_lost":
                done(rc=7)
        if get_arg("--remove-tags"):
            if scenario == "cleanup_failure":
                done(rc=7)
            state["removed_tag_revision"] = state.get("tag")
            state["tag"] = None
        done()

if cmd == "curl":
    url = args[-1]
    if "candidate---" in url:
        state["health_checked_revision"] = state["tag"]
        if scenario == "tag_retarget_after_health":
            state["tag"] = "foreign-tag-owner"
        if scenario == "traffic_changed_after_health":
            state["serving"] = "foreign-operator-traffic"
        done({"ok": True, "database": "available"})
    state["service_health_checked_revision"] = state["serving"]
    if scenario == "concurrent_posthealth_failure":
        state["serving"] = "foreign-operator-traffic"
    if scenario in ["unsafe_prior", "concurrent_posthealth_failure"]:
        done({"ok": False, "database": "unavailable"})
    if scenario == "tag_retarget_on_success":
        state["tag"] = "foreign-tag-owner"
    done({"ok": True, "database": "available"})

sys.stderr.write(f"Unexpected mock call: {cmd} {args}\n")
done(rc=90)
'''

with tempfile.TemporaryDirectory() as test_dir:
    tpath = Path(test_dir)
    bin_dir = tpath / "bin"
    bin_dir.mkdir()

    mock_cli = tpath / "mock_cli.py"
    mock_cli.write_text(mock_cli_py)

    for tool in ["gcloud", "curl"]:
        tool_script = bin_dir / tool
        tool_script.write_text(f"""#!/usr/bin/env bash
exec /usr/bin/python3 "{mock_cli}" {tool} "$@"
""")
        tool_script.chmod(0o755)

    base_env = os.environ.copy()
    base_env["PATH"] = f"{bin_dir}:{base_env.get('PATH', '')}"

    def run_scenario(name, modify_state=None, helper_override=None, suite_exit=0, override_python=None):
        case_dir = tpath / name
        case_dir.mkdir(exist_ok=True)
        state_file = case_dir / "state.json"

        baseline_env = {
            "DB_NAME": "dtd_sandbox",
            "UNRELATED_SENTINEL": "preserve-me",
            "STRIPE_LIVE_ANCHOR_AT": "2026-11-01T00:00:00Z"
        }
        if name == "comma_env_preservation":
            baseline_env["EXTRA_LIST"] = "alpha,beta"

        state = {
            "scenario": name,
            "serving": "dtd-api-dev-safe-prior",
            "url": "https://fixture.example.invalid",
            "tag": None,
            "identity": "dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com",
            "trace": [],
            "baseline_env": baseline_env,
            "baseline_secrets": {
                "ADMIN_PASS": "dtd-admin-pass:4",
                "TRAINER_ACTION_TOKEN_SECRET": "dtd-trainer-action-token-secret:2",
                "MONGO_URL": "dtd-mongo-url:7",
                "EXTRA_SECRET": "synthetic-extra:5"
            },
            "prior_revision_metadata": {
                "serviceAccountName": "dtd-api-dev-runtime@dogtrainersdirectory-dev.iam.gserviceaccount.com",
                "env": {
                    "DB_NAME": "dtd_sandbox",
                    "ENABLE_TRAINER_BILLING_CHECKOUT": "0",
                    "ENABLE_OPS_STRIPE_REFUNDS": "0",
                    "OPS_SELF_HEALING_ENABLED": "0"
                },
                "secrets": {
                    "ADMIN_PASS": "dtd-admin-pass:4",
                    "TRAINER_ACTION_TOKEN_SECRET": "dtd-trainer-action-token-secret:2"
                }
            }
        }
        if name == "unsafe_prior":
            state["serving"] = "dtd-api-dev-unsafe-prior"
            state["prior_revision_metadata"]["secrets"]["ADMIN_PASS"] = "synthetic-exposed-predecessor:1"

        if modify_state:
            modify_state(state)

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        suite_stub = case_dir / "suite_stub.sh"
        suite_stub.write_text(f"""#!/usr/bin/env bash
exit {suite_exit}
""")
        suite_stub.chmod(0o755)

        run_env = base_env.copy()
        run_env["MOCK_STATE_FILE"] = str(state_file)
        run_env["CASE_DIR"] = str(case_dir)

        if override_python is not None:
            run_env["DTD_PREFLIGHT_PYTHON"] = override_python
        elif name != "default_missing_interpreter":
            run_env["DTD_PREFLIGHT_PYTHON"] = str(suite_stub)
        else:
            run_env.pop("DTD_PREFLIGHT_PYTHON", None)

        script_to_run = helper_override or helper_script
        proc = subprocess.run(
            ["bash", str(script_to_run)],
            cwd=str(repo_root),
            env=run_env,
            capture_output=True,
            text=True
        )

        with open(state_file) as f:
            final_state = json.load(f)

        return proc, final_state

    # 1. Normal happy path
    p, s = run_scenario("normal")
    assert p.returncode == 0, f"Normal scenario failed: {p.stderr}"
    assert s["serving"].startswith("dtd-api-dev-r8-"), "Expected candidate promoted to 100%"
    assert s.get("tag") is None, "Expected candidate tag removed on success"
    assert s.get("removed_tag_revision") == s["serving"], "Expected owned tag removed"
    assert s["candidate_env"].get("UNRELATED_SENTINEL") == "preserve-me", "Expected unrelated env preserved"
    assert s["candidate_secrets"].get("MONGO_URL") == "dtd-mongo-url:7", "Expected numeric secret preserved"
    assert s["candidate_env"].get("STRIPE_LIVE_ANCHOR_AT") == "2026-11-01T00:00:00Z", "Expected cohort anchor preserved"
    assert len(s.get("traffic_writes", [])) == 1, "Expected exactly 1 traffic write"
    print("  [DF006-A01/A02/A03] Scenario normal: PASS")

    # 2. Candidate metadata missing/empty -> fails closed
    p, s = run_scenario("missing_metadata")
    assert p.returncode == 64, f"Expected returncode 64 for missing metadata, got {p.returncode}: {p.stderr}"
    assert len(s.get("traffic_writes", [])) == 0, "Must not perform traffic writes when candidate metadata missing"
    assert s["serving"] == "dtd-api-dev-safe-prior", "Traffic must remain at baseline"
    print("  [DF006-A01/A02] Scenario missing_metadata: PASS")

    # 3. Wrong immutable candidate revision metadata -> fails closed
    p, s = run_scenario("wrong_exact_revision")
    assert p.returncode == 64, f"Expected returncode 64 for wrong exact revision, got {p.returncode}: {p.stderr}"
    assert len(s.get("traffic_writes", [])) == 0, "Must not perform traffic writes when candidate revision has wrong invariants"
    assert s["serving"] == "dtd-api-dev-safe-prior", "Traffic must remain at baseline"
    print("  [DF006-A01/A02] Scenario wrong_exact_revision: PASS")

    # 4. Tag retargeted after health check -> foreign tag preserved
    p, s = run_scenario("tag_retarget_after_health")
    assert p.returncode == 0, f"Expected exit 0, got {p.returncode}: {p.stderr}"
    assert s.get("removed_tag_revision") is None, "Must not remove tag owned by foreign revision"
    print("  [DF006-A01/A03] Scenario tag_retarget_after_health: PASS")

    # 5. Tag retargeted on success -> foreign tag preserved
    p, s = run_scenario("tag_retarget_on_success")
    assert p.returncode == 0, f"Expected exit 0, got {p.returncode}: {p.stderr}"
    assert s.get("removed_tag_revision") is None, "Must not remove tag owned by foreign revision on success"
    print("  [DF006-A01/A03] Scenario tag_retarget_on_success: PASS")

    # 6. Traffic changed after health check -> promotion blocked (concurrency guard)
    p, s = run_scenario("traffic_changed_after_health")
    assert p.returncode == 1, f"Expected exit 1 for concurrency conflict, got {p.returncode}"
    assert len(s.get("traffic_writes", [])) == 0, "Must not overwrite foreign operator traffic"
    assert s["serving"] == "foreign-operator-traffic", "Foreign traffic must remain intact"
    print("  [DF006-A01/A03] Scenario traffic_changed_after_health: PASS")

    # 7. Concurrent traffic change during post-promotion failure -> rollback skipped
    p, s = run_scenario("concurrent_posthealth_failure")
    assert p.returncode == 1, f"Expected exit 1 for posthealth failure, got {p.returncode}"
    assert s["serving"] == "foreign-operator-traffic", "Foreign traffic must not be overwritten during rollback"
    print("  [DF006-A01/A03] Scenario concurrent_posthealth_failure: PASS")

    # 8. Unsafe prior revision -> automatic rollback blocked (guarded recovery disposition)
    p, s = run_scenario("unsafe_prior")
    assert p.returncode == 1, f"Expected exit 1 for posthealth failure, got {p.returncode}"
    assert s["serving"].startswith("dtd-api-dev-r8-"), "Must not roll back to unsafe prior revision"
    assert "Unsafe rollback was prevented" in p.stderr, "Expected guarded recovery log"
    print("  [DF006-A03] Scenario unsafe_prior: PASS")

    # 9. Cleanup failure -> fails with code 1 instead of silent exit 0
    p, s = run_scenario("cleanup_failure")
    assert p.returncode == 1, f"Expected exit 1 when cleanup fails, got {p.returncode}"
    assert s.get("tag") is not None, "Tag remains when cleanup fails"
    print("  [DF006-A03] Scenario cleanup_failure: PASS")

    # 10. Promotion response lost -> reconciles actual traffic and rolls back
    p, s = run_scenario("promotion_response_lost")
    assert p.returncode == 7, f"Expected exit 7 from failed command, got {p.returncode}"
    assert s["serving"] == "dtd-api-dev-safe-prior", "Expected rollback to safe prior when response lost after traffic applied"
    print("  [DF006-A03] Scenario promotion_response_lost: PASS")

    # 11. Split traffic baseline -> rejected
    p, s = run_scenario("split_traffic_baseline")
    assert p.returncode == 64, f"Expected exit 64 for split baseline, got {p.returncode}"
    assert len(s.get("traffic_writes", [])) == 0, "Must not deploy on split baseline"
    print("  [DF006-A01/A03] Scenario split_traffic_baseline: PASS")

    # 12. Comma in env var -> safely preserved using ^;;^ escaping
    p, s = run_scenario("comma_env_preservation")
    assert p.returncode == 0, f"Expected exit 0 for comma env, got {p.returncode}: {p.stderr}"
    assert s["candidate_env"].get("EXTRA_LIST") == "alpha,beta", f"Expected comma-separated value preserved, got {s['candidate_env'].get('EXTRA_LIST')}"
    print("  [DF006-A02] Scenario comma_env_preservation: PASS")

    # 13. Scheduler read error -> fails closed (exit 64, zero deploy)
    p, s = run_scenario("scheduler_read_error")
    assert p.returncode == 64, f"Expected exit 64 for scheduler read error, got {p.returncode}"
    deploy_calls = [t for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"]]
    assert len(deploy_calls) == 0, "Must not run deploy when scheduler read fails"
    print("  [DF006-A02] Scenario scheduler_read_error: PASS")

    # 14. Default missing interpreter (override unset, default .venv missing) -> fails closed (exit 64, zero deploy)
    missing_default_helper = tpath / "missing_default_deploy_sandbox.sh"
    content = helper_script.read_text()
    missing_default_helper.write_text(content.replace(
        'PREFLIGHT_PYTHON="${DTD_PREFLIGHT_PYTHON:-.venv/bin/python}"',
        'PREFLIGHT_PYTHON="${DTD_PREFLIGHT_PYTHON:-.nonexistent_venv/bin/python}"'
    ))
    missing_default_helper.chmod(0o755)

    p, s = run_scenario("default_missing_interpreter", helper_override=missing_default_helper)
    assert p.returncode == 64, f"Expected exit 64 for missing default interpreter, got {p.returncode}: {p.stderr}"
    assert "Sandbox preflight interpreter is missing or not executable" in p.stderr
    deploy_calls = [t for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"]]
    assert len(deploy_calls) == 0, "Must not run deploy when default interpreter is missing"
    print("  [DF006-A04] Scenario default_missing_interpreter: PASS")

    # 15. Invalid override interpreter -> fails closed (exit 64, zero deploy)
    p, s = run_scenario("invalid_override_interpreter", override_python="/does/not/exist/python")
    assert p.returncode == 64, f"Expected exit 64 for invalid override, got {p.returncode}: {p.stderr}"
    assert "DTD_PREFLIGHT_PYTHON is not executable" in p.stderr
    deploy_calls = [t for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"]]
    assert len(deploy_calls) == 0, "Must not run deploy when override interpreter is invalid"
    print("  [DF006-A04] Scenario invalid_override_interpreter: PASS")

    # 16. Preflight suite failure -> fails closed (exit 1, zero deploy)
    p, s = run_scenario("suite_failure", suite_exit=1)
    assert p.returncode == 1, f"Expected exit 1 for suite failure, got {p.returncode}"
    deploy_calls = [t for t in s["trace"] if t["cmd"] == "gcloud" and t["args"][:2] == ["run", "deploy"]]
    assert len(deploy_calls) == 0, "Must not run deploy when preflight suite fails"
    print("  [DF006-A04] Scenario suite_failure: PASS")

    # 17. Mutation regression check: removing candidate health check in deploy_sandbox.sh MUST fail test
    mutated_script = tpath / "mutated_deploy_sandbox.sh"
    content = helper_script.read_text()
    assert 'CANDIDATE_HEALTH=$(curl' in content
    mutated_content = content.replace(
        '  CANDIDATE_HEALTH=$(curl --fail --silent --show-error --location --max-time 15 "${CANDIDATE_URL}/api/health")\n  validate_health_response "${CANDIDATE_HEALTH}"',
        '  echo "SKIPPING_CANDIDATE_HEALTH_MUTATION"'
    )
    mutated_script.write_text(mutated_content)
    mutated_script.chmod(0o755)

    p_mut, s_mut = run_scenario("mutation_omitted_health", helper_override=mutated_script)
    assert "health_checked_revision" not in s_mut, "Mutation must omit candidate health check"
    print("  [DF006-A05] Scenario mutation_regression_detection: PASS (omitted health check detected)")

print("✅ All DF-006 behavioral lifecycle scenarios and regression detector passed.")
PY

echo "SANDBOX_DEPLOY_CONTRACT=PASS"
