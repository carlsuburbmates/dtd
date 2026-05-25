#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const repoRoot = path.resolve(__dirname, "..");
const serverPath = path.join(repoRoot, "backend", "server.py");
const copyGuardPath = path.join(repoRoot, "scripts", "check_frontend_copy_guard.js");
const failures = [];

function check(condition, message) {
  if (!condition) failures.push(message);
}

function readText(filePath, label) {
  if (!fs.existsSync(filePath)) {
    failures.push(`${label} missing: ${path.relative(repoRoot, filePath)}`);
    return "";
  }
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (err) {
    failures.push(`${label} unreadable: ${path.relative(repoRoot, filePath)} (${err.message})`);
    return "";
  }
}

const serverText = readText(serverPath, "backend server");
if (serverText) {
  check(
    serverText.includes("PUBLIC_MATCHING_ENABLED"),
    "matching gate symbol missing: PUBLIC_MATCHING_ENABLED",
  );
  check(
    serverText.includes("def _require_public_matching("),
    "matching gate function missing: _require_public_matching",
  );
  check(
    serverText.includes('_require_public_matching("Public matching")'),
    "matching gate check missing on match path",
  );
  check(
    serverText.includes('_require_public_matching("Public contact release")'),
    "matching gate check missing on intro/contact path",
  );

  check(
    serverText.includes('@api.get("/claims/validate")'),
    "claims validate endpoint missing",
  );
  check(
    serverText.includes('@api.post("/owner-waitlist")'),
    "owner waitlist endpoint missing",
  );

  // Phase/readiness layer — required since 2026-05-25
  check(
    serverText.includes("PUBLIC_LAUNCH_PHASE"),
    "phase symbol missing: PUBLIC_LAUNCH_PHASE",
  );
  check(
    serverText.includes("_get_or_create_launch_phase_state("),
    "phase symbol missing: _get_or_create_launch_phase_state",
  );
  check(
    serverText.includes("phase_readiness_snapshots"),
    "phase symbol missing: phase_readiness_snapshots collection",
  );
  check(
    serverText.includes("phase_transition_decisions"),
    "phase symbol missing: phase_transition_decisions collection",
  );
}

if (!fs.existsSync(copyGuardPath)) {
  failures.push("copy guard script missing: scripts/check_frontend_copy_guard.js");
} else {
  const copyGuardRun = spawnSync(process.execPath, [copyGuardPath], {
    cwd: repoRoot,
    encoding: "utf8",
  });
  if (copyGuardRun.status !== 0) {
    failures.push("copy guard check failed: scripts/check_frontend_copy_guard.js");
    const mergedOutput = `${copyGuardRun.stdout || ""}\n${copyGuardRun.stderr || ""}`.trim();
    if (mergedOutput) {
      const firstLines = mergedOutput
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .slice(0, 5);
      for (const line of firstLines) {
        failures.push(`copy guard detail: ${line}`);
      }
    }
  }
}

if (failures.length > 0) {
  console.log("PRELAUNCH_RELEASE_GATE=FAIL");
  for (const reason of failures) {
    console.log(`REASON: ${reason}`);
  }
  process.exit(1);
}

console.log("PRELAUNCH_RELEASE_GATE=PASS");
