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

const bannedLegacyPhrases = ["A$5", "trial-free"];
const bannedCommercialClaims = [
  "exclusive top-slot placement",
  "featured across diagnostic match results",
  "change suburb anytime",
];

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

// Commercial claims must preserve two-slot capacity and fit-first matching.
const pricingPath = path.join(repoRoot, "frontend/src/pages/Pricing.jsx");
const pricingText = fs.readFileSync(pricingPath, "utf8");
for (const phrase of bannedCommercialClaims) {
  for (const hit of findMatches(pricingText, phrase)) {
    violations.push({
      file: path.relative(repoRoot, pricingPath),
      line: lineFromIndex(pricingText, hit.index),
      message: `retired commercial claim: "${phrase}"`,
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
console.log("Commercial claim check: two-slot capacity and fit-first messaging preserved");
