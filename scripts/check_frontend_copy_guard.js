#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const frontendSrc = path.join(repoRoot, "frontend", "src");
const publicPolicyPath = path.join(frontendSrc, "lib", "publicPolicy.js");

const targetedPages = [
  "frontend/src/pages/About.jsx",
  "frontend/src/pages/FAQ.jsx",
  "frontend/src/pages/Home.jsx",
  "frontend/src/pages/Pricing.jsx",
  "frontend/src/pages/Terms.jsx",
  "frontend/src/pages/TrainerDetail.jsx",
  "frontend/src/pages/Trainers.jsx",
  "frontend/src/pages/Trust.jsx",
  "frontend/src/pages/Submit.jsx",
].map((p) => path.join(repoRoot, p));

const bannedLegacyPhrases = ["A$5", "trial-free", "per-intro fee"];

function walkFiles(dir) {
  const out = [];
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      out.push(...walkFiles(full));
      continue;
    }
    if (/\.(js|jsx|ts|tsx)$/.test(name)) out.push(full);
  }
  return out;
}

function lineFromIndex(text, idx) {
  return text.slice(0, idx).split("\n").length;
}

function findMatches(text, phrase) {
  const matches = [];
  const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(escaped, "gi");
  let m;
  while ((m = re.exec(text))) {
    matches.push({ index: m.index, value: m[0] });
  }
  return matches;
}

const violations = [];

// Rule 1+2: targeted pages must not contain hardcoded legacy phrases.
for (const filePath of targetedPages) {
  const text = fs.readFileSync(filePath, "utf8");
  for (const phrase of bannedLegacyPhrases) {
    for (const hit of findMatches(text, phrase)) {
      violations.push({
        file: path.relative(repoRoot, filePath),
        line: lineFromIndex(text, hit.index),
        message: `banned phrase in targeted page: \"${phrase}\"`,
      });
    }
  }
}

// Rule 4: legacy fallback wording allowed in publicPolicy.js only.
for (const filePath of walkFiles(frontendSrc)) {
  const text = fs.readFileSync(filePath, "utf8");
  for (const phrase of bannedLegacyPhrases) {
    for (const hit of findMatches(text, phrase)) {
      if (filePath !== publicPolicyPath) {
        violations.push({
          file: path.relative(repoRoot, filePath),
          line: lineFromIndex(text, hit.index),
          message: `legacy phrase \"${phrase}\" is only allowed in frontend/src/lib/publicPolicy.js`,
        });
      }
    }
  }
}

// Rule 3: Home owner-facing prelaunch section must not contain direct "Melbourne-wide" claim.
const homePath = path.join(repoRoot, "frontend/src/pages/Home.jsx");
const homeText = fs.readFileSync(homePath, "utf8");
const prelaunchStart = homeText.indexOf('data-testid="match-coming-soon"');
const prelaunchFallbackStart = homeText.indexOf('data-testid="owner-waitlist-form"');
const start = prelaunchStart >= 0 ? prelaunchStart : prelaunchFallbackStart;

if (start < 0) {
  violations.push({
    file: "frontend/src/pages/Home.jsx",
    line: 1,
    message: "could not locate prelaunch owner-facing section for Melbourne-wide guard",
  });
} else {
  const end = homeText.indexOf(") : (", start);
  const section = homeText.slice(start, end > start ? end : start + 4000);
  const re = /melbourne-wide/i;
  const hit = re.exec(section);
  if (hit) {
    violations.push({
      file: "frontend/src/pages/Home.jsx",
      line: lineFromIndex(homeText, start + hit.index),
      message: 'direct "Melbourne-wide" claim found in owner-facing prelaunch section',
    });
  }
}

if (violations.length) {
  console.error("COPY_GUARD_CHECK=FAIL");
  for (const v of violations) {
    console.error(`- ${v.file}:${v.line} ${v.message}`);
  }
  process.exit(1);
}

console.log("COPY_GUARD_CHECK=PASS");
console.log(`Checked targeted pages: ${targetedPages.length}`);
console.log("Legacy phrases allowed only in frontend/src/lib/publicPolicy.js");
console.log('Home prelaunch section check: no direct "Melbourne-wide" claim');
