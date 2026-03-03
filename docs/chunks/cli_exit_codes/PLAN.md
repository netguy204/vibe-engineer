<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The implementation follows a test-driven development approach, updating tests first to define the expected exit code behavior, then modifying the CLI code to match.

The core principle being established:
- **Exit code 0**: Command succeeded (including "no results found" - this is a valid, successful outcome)
- **Exit code 1**: Command failed due to an error (validation errors, missing files, parse errors, etc.)

This aligns with standard UNIX conventions where exit code 0 means success, and follows the pattern already used by `ve friction list` and `ve chunk list-proposed`.

The changes are localized to CLI modules only - the underlying domain logic remains unchanged. Each list command will be updated to treat "empty results" as success (exit 0) rather than error (exit 1).

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk touches CLI commands that manage workflow artifacts. The changes are purely presentation-layer (exit codes), not affecting the underlying artifact lifecycle logic.

## Sequence

### Step 1: Update tests to expect exit code 0 for empty results

Update the existing tests that currently expect exit code 1 for "no results found" scenarios to expect exit code 0 instead. This establishes the new contract first (TDD approach).

**Files to modify:**
- `tests/test_chunk_list.py`: Change `test_empty_project_exits_with_error` to expect exit code 0
- `tests/test_narrative_list.py`: Change `test_empty_project_exits_with_error` to expect exit code 0
- `tests/test_investigation_list.py`: Change `test_empty_project_exits_with_error` and `test_state_filter_works` (SOLVED filter case) to expect exit code 0
- `tests/test_subsystem_list.py`: Change `test_empty_project_exits_with_error` to expect exit code 0

Also update test names and docstrings to reflect the new behavior (e.g., "exits_with_success" instead of "exits_with_error").

### Step 2: Fix chunk list exit codes

Modify `src/cli/chunk.py` to exit with code 0 when no chunks are found.

**Lines to change:**
- Line 445: Change `raise SystemExit(1)` to `raise SystemExit(0)` for the main list case

Note: The `--current`, `--last-active`, and `--recent` flags should continue to exit with code 1 when no matching chunk is found, because these flags explicitly request a specific chunk type and not finding one is an error condition (the operator is asking "give me THE current chunk" not "list all chunks").

### Step 3: Fix investigation list exit codes

Modify `src/cli/investigation.py` to exit with code 0 when no investigations are found.

**Line to change:**
- Line 143: Change `raise SystemExit(1)` to `raise SystemExit(0)`

### Step 4: Fix narrative list exit codes

Modify `src/cli/narrative.py` to exit with code 0 when no narratives are found.

**Line to change:**
- Line 130: Change `raise SystemExit(1)` to `raise SystemExit(0)`

### Step 5: Fix subsystem list exit codes

Modify `src/cli/subsystem.py` to exit with code 0 when no subsystems are found.

**Line to change:**
- Line 58: Change `raise SystemExit(1)` to `raise SystemExit(0)`

### Step 6: Make migration list exit code explicit

Modify `src/cli/migration.py` to explicitly use `raise SystemExit(0)` for empty results instead of implicit return.

**Line to change:**
- Line 101-102: Change `return` to `raise SystemExit(0)` for consistency, even though the behavior is the same (implicit return = exit 0)

### Step 7: Update SPEC.md to document exit code convention

Add a new section to `docs/trunk/SPEC.md` documenting the exit code convention:

**Location:** After the "CLI" section in SPEC.md (around line 379), add a new subsection called "Exit Code Convention" that documents:
- Exit code 0 means "command succeeded" including "no results found"
- Exit code 1 means "command failed due to an error"
- List of error conditions that trigger exit code 1

Also update individual command documentation in SPEC.md to reflect the new exit code behavior:
- Line 480: Update `ve chunk list` exit codes
- Line 542: Update `ve subsystem list` exit codes
- Line 625: Update `ve investigation list` exit codes

### Step 8: Run tests to verify all changes work correctly

Run the full test suite to ensure:
1. All updated tests pass with the new expected exit codes
2. No regression in other tests
3. Error cases still exit with code 1

```bash
uv run pytest tests/test_chunk_list.py tests/test_narrative_list.py tests/test_investigation_list.py tests/test_subsystem_list.py tests/test_friction_cli.py -v
```

## Dependencies

None. This chunk has no dependencies on other chunks in the `arch_consolidation` narrative.

## Risks and Open Questions

1. **Breaking change for scripts**: Users who rely on the current exit code behavior may have scripts that break. However, the new behavior is more correct per UNIX conventions, and the previous behavior was inconsistent across commands.

2. **Special flags like --current**: The `--current`, `--last-active`, and `--recent` flags for `ve chunk list` are designed to return a single specific chunk. When no matching chunk exists, this is an error condition because the operator explicitly requested a specific result. These should continue to exit with code 1.

3. **Status filtering edge cases**: When using `--status ACTIVE` and no ACTIVE chunks exist, should this exit 0 or 1? The decision is exit 0 - the command succeeded at listing (which returned empty results). The filter is not requesting a specific single item.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
