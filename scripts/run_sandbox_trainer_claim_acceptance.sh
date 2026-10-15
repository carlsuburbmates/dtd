#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="dogtrainersdirectory-dev"
execute=0
for argument in "$@"; do
    if [[ "${argument}" == "--execute" ]]; then
        execute=1
        break
    fi
done

if [[ "${execute}" -eq 0 ]]; then
    exec .venv/bin/python scripts/run_sandbox_trainer_claim_acceptance.py "$@"
fi

if [[ ! -t 0 ]]; then
    printf '%s\n' "Execute mode requires an interactive terminal for the bounded browser handoff." >&2
    exit 2
fi

export DTD_SANDBOX_PROJECT_ID="${PROJECT_ID}"
export DTD_SANDBOX_DATABASE="dtd_sandbox"
export MONGO_URL="$(gcloud secrets versions access latest --project="${PROJECT_ID}" --secret=dtd-mongo-url)"

exec .venv/bin/python scripts/run_sandbox_trainer_claim_acceptance.py "$@"
