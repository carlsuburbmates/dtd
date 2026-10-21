from pathlib import Path
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts" / "verify_sandbox_ops_phase3_live.mjs"
EXPECTED_RUNNER_SOURCE = '''/**
 * Retired unsafe live acceptance runner.
 *
 * The historical version embedded an administrator credential, injected it
 * into browser storage, and could create persistent business records without
 * deterministic cleanup. It must not be restored or executed.
 */

console.error(
  "This live acceptance runner has been retired. It makes no network requests. " +
    "Use the current approved sandbox acceptance procedures with synthetic fixtures and verified cleanup."
);
process.exitCode = 2;
'''


def test_retired_ops_live_runner_fails_closed_without_network_access():
    source = RUNNER.read_text()
    assert source == EXPECTED_RUNNER_SOURCE, "review any runner change before relaxing this fail-closed contract"

    node = shutil.which("node")
    assert node, "Node.js is required to verify the retired runner contract"

    result = subprocess.run(
        [node, str(RUNNER)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert "has been retired" in result.stderr
    assert "no network requests" in result.stderr
    assert result.stdout == ""
