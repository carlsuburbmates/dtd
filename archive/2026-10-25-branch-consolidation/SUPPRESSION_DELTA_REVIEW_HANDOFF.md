# Historical suppression handoff — superseded

Preserved on 25 October 2026. The original handoff below predates accepted commit `50f3c594d611bede8b7a610d7b09fb3fd8680f23`. Its uncommitted/awaiting-review wording is historical; current status is governed by the R1 release evidence and current-state record. It is not an instruction to restart accepted work.

---

# DF-043 Suppression Fix — Independent Delta Review Handoff

**Base:** accepted R0 `1ac4138e4d82991501139298cc624be732661119`  
**Worktree:** `/Users/carlg/.codex/worktrees/dtd-suppression-safety/dtd`  
**Current state:** three source/test files modified plus this handoff; uncommitted. No push, PR, provider mutation or deployment.

## Finding and reproduction

On the accepted baseline, an isolated synthetic invocation of the exact `/api/internal/jobs/trainer-ingest` handler reproduced re-publication for both (a) an existing unclaimed trainer referenced by `delisted_entities.trainer_id` after its identity fields changed and (b) a new candidate matching a delisted canonical identity. With Guardian enabled, both cases returned job success, promoted their queue rows, published/inserted one trainer and ended with Guardian `clean`. No sandbox or production trainer data was changed.

## Proposed bounded delta

- `backend/services/deduplication.py`: allow canonical suppression lookup to include an authoritative `trainer_id` match.
- `backend/services/ingestion_manager.py`: check suppression before fetch, after extracted identity, and against the existing trainer ID before mutation; mark suppressed queue rows with an explicit reason rather than promoting them.
- `backend/tests/test_ingestion_manager_unit.py`: model `$or` in the fake DB; exercise both scenarios through the scheduler route with Guardian enabled; isolate ABN, normalized phone and website-domain suppression keys and prove suppression occurs before fetch.

## Verification

Command:

```text
/Users/carlg/Documents/AI-Coding/dtd/.venv/bin/pytest -q backend/tests/test_ingestion_manager_unit.py backend/tests/test_ops_workflow_reconciliation.py -k 'ingestion_manager or trainer_ingest or trainer_delisting_and_compliance_suppression or does_not_republish_delisted or does_not_insert_new_identity'
```

Result after independent review feedback: **17 passed, 15 deselected**. `git diff --check` passed. Warnings were dependency/FastAPI deprecations; no failures.

## Review request

Review the actual cumulative diff against the stated base and verify:

1. Existing delisted trainers cannot be reactivated/re-published even if identity fields changed.
2. New inserts remain suppressed for every canonical identity key used by `delisted_entities`.
3. Suppression is checked before any trainer/source-success mutation and behaves correctly for dry-run, missing queue id, claimed records and Guardian remediation.
4. Queue status/reason and summary semantics are idempotent and do not accidentally hide non-suppressed failures.
5. The existing-trainer case has stale ABN, phone and website-domain values in its delisting snapshot; the new-record parameterized cases isolate each canonical identity key. Regression tests exercise the scheduler handler's ingestion path while mocking external providers and the OIDC boundary; separate endpoint tests cover OIDC behavior. No production/provider state is involved.

**Promotion gate:** no commit, push, PR, deployment or scheduler resume until this exact delta is independently accepted. After acceptance, use the authorized developer sandbox workflow, verify deployed source identity and affected negative/positive cases, confirm fixtures are absent, prove rollback, then decide on scheduler restoration. R0 itself is unchanged.
