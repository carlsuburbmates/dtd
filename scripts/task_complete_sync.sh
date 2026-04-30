#!/usr/bin/env bash
set -euo pipefail

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  echo "Refusing to sync from non-main branch: $branch" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  msg="task: autosync $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git add -A
  git commit -m "$msg"
fi

# Keep local aligned before push.
git pull --rebase origin main

git push origin main

echo "Synced main to origin/main"
