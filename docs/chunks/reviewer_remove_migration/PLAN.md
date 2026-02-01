<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a cleanup chunk that removes dead code. The migration from `DECISION_LOG.md` to
per-file decisions has already been executed, producing 15 decision files in
`docs/reviewers/baseline/decisions/`. The migration code is no longer needed.

The approach is straightforward:
1. Delete the migration module and its tests
2. Remove the CLI command registration
3. Delete the now-obsolete `DECISION_LOG.md` source file
4. Verify no orphan imports remain
5. Confirm all tests still pass

No new code is written. Per `docs/trunk/TESTING_PHILOSOPHY.md`, tests that verified
the migration behavior are deleted along with the code - there's nothing left to test.

## Subsystem Considerations

No subsystems are relevant. This chunk only deletes dead code.

## Sequence

### Step 1: Remove CLI command from ve.py

Delete the `migrate-decisions` command and its decorator from `src/ve.py`.

Location: `src/ve.py`, lines 4540-4566 (the `@reviewer.command("migrate-decisions")` function)

Action: Delete the entire function and its backreference comment.

### Step 2: Delete migration module

Delete the migration module file.

Location: `src/decision_migration.py`

Action: `rm src/decision_migration.py`

### Step 3: Delete migration tests

Delete the test file for the migration module.

Location: `tests/test_decision_migration.py`

Action: `rm tests/test_decision_migration.py`

### Step 4: Delete DECISION_LOG.md

Delete the now-obsolete decision log file. The migrated entries are preserved in
the per-file decisions at `docs/reviewers/baseline/decisions/`.

Location: `docs/reviewers/baseline/DECISION_LOG.md`

Action: `rm docs/reviewers/baseline/DECISION_LOG.md`

### Step 5: Verify no orphan imports

Search the codebase to confirm no remaining imports of `decision_migration`.

Action: `grep -r "decision_migration" --include="*.py" src/ tests/`

Expected result: No matches. If any matches remain, delete those import statements.

### Step 6: Run tests

Verify all remaining tests pass.

Action: `uv run pytest tests/`

Expected result: All tests pass. The deleted tests should not cause failures since
they're no longer present.

### Step 7: Update parent chunk status

The `reviewer_use_decision_files` chunk has code references pointing to the deleted
files. After this chunk completes, those references become stale.

Action: Update `docs/chunks/reviewer_use_decision_files/GOAL.md`:
- Change `status` to `SUPERSEDED`
- The code_references to `decision_migration.py` and `test_decision_migration.py`
  are no longer valid, but the chunk's work (establishing the per-file decision
  system) remains ACTIVE

Alternatively, the code_references could be edited to remove the deleted file
references while keeping status as ACTIVE since the remaining references
(to `ve.py`, `reviewers.py`, templates) are still valid.

**Decision needed:** Consult operator on preferred approach during implementation.

## Dependencies

No implementation dependencies. The migration was already executed by
`reviewer_use_decision_files`, and this chunk only removes the migration code.

## Risks and Open Questions

- **Low risk**: If any code imports `decision_migration` that we miss, tests will
  fail with an import error. Easy to detect and fix.

- **Parent chunk handling**: The `reviewer_use_decision_files` chunk references the
  files being deleted. We need to decide whether to mark it SUPERSEDED or just
  update its code_references. Either approach is valid per workflow artifacts rules.

## Deviations

<!-- Populated during implementation -->