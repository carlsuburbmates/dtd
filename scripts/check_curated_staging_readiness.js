#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const repoRoot = path.resolve(__dirname, "..");
const manifestPath = path.join(repoRoot, "docs", "process", "IMPLEMENTATION_EVIDENCE_MANIFEST.md");
const sectionHeader = "## Guarded files/groups for curated staging";

const reasons = [];
const fileChecks = [];

function fail(reason) {
  reasons.push(reason);
}

function readManifest() {
  if (!fs.existsSync(manifestPath)) {
    fail("manifest missing: docs/process/IMPLEMENTATION_EVIDENCE_MANIFEST.md");
    return "";
  }
  try {
    return fs.readFileSync(manifestPath, "utf8");
  } catch (err) {
    fail(`manifest unreadable: ${err.message}`);
    return "";
  }
}

function extractCuratedSection(text) {
  const start = text.indexOf(sectionHeader);
  if (start < 0) {
    fail('curated section missing: "Guarded files/groups for curated staging"');
    return "";
  }
  const afterStart = text.slice(start + sectionHeader.length);
  const nextHeaderIdx = afterStart.search(/\n##\s+/);
  if (nextHeaderIdx < 0) {
    return afterStart;
  }
  return afterStart.slice(0, nextHeaderIdx);
}

function extractFiles(sectionText) {
  const files = [];
  const seen = new Set();
  const lines = sectionText.split(/\r?\n/);
  for (const line of lines) {
    const m = line.match(/`([^`]+)`/);
    if (!m) continue;
    const candidate = (m[1] || "").trim();
    if (!candidate) continue;
    // Treat only relative repository file paths in the curated section as file entries.
    if (candidate.includes(" ")) continue;
    if (!candidate.includes("/")) continue;
    if (candidate.startsWith("http://") || candidate.startsWith("https://")) continue;
    if (!seen.has(candidate)) {
      seen.add(candidate);
      files.push(candidate);
    }
  }
  if (files.length === 0) {
    fail("curated section empty: no file paths found");
  }
  return files;
}

function isTrackedByGit(relPath) {
  const out = spawnSync("git", ["ls-files", "--error-unmatch", "--", relPath], {
    cwd: repoRoot,
    encoding: "utf8",
  });
  return out.status === 0;
}

const manifestText = readManifest();
const curatedSection = manifestText ? extractCuratedSection(manifestText) : "";
const curatedFiles = curatedSection ? extractFiles(curatedSection) : [];

for (const relPath of curatedFiles) {
  const absPath = path.join(repoRoot, relPath);
  const exists = fs.existsSync(absPath);
  if (!exists) {
    fail(`listed file missing: ${relPath}`);
    fileChecks.push({ path: relPath, exists: false, gitStatus: "missing" });
    continue;
  }
  const tracked = isTrackedByGit(relPath);
  fileChecks.push({ path: relPath, exists: true, gitStatus: tracked ? "tracked" : "untracked" });
}

if (reasons.length > 0) {
  console.log("CURATED_STAGING_READINESS=FAIL");
  for (const reason of reasons) {
    console.log(`REASON: ${reason}`);
  }
  for (const row of fileChecks) {
    console.log(`FILE: ${row.path} | exists=${row.exists ? "yes" : "no"} | git=${row.gitStatus}`);
  }
  process.exit(1);
}

console.log("CURATED_STAGING_READINESS=PASS");
for (const row of fileChecks) {
  console.log(`FILE: ${row.path} | exists=yes | git=${row.gitStatus}`);
}
