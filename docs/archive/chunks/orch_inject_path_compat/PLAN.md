<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The codebase already has a well-established pattern for normalizing artifact paths: the `strip_artifact_path_prefix()` function in `src/external_refs.py`. This function handles the exact variations specified in the success criteria:
- Trailing slashes: `docs/chunks/foo/` → `foo`
- Full paths: `docs/chunks/foo` → `foo`
- Short prefix: `chunks/foo` → `foo`
- Short names: `foo` → `foo`

This same pattern is used by 10+ other commands including `chunk activate`, `chunk status`, `chunk validate`, `narrative status`, `subsystem status`, etc. Following this pattern ensures consistency with the rest of the codebase.

**Strategy**: Add a single line of path normalization in the `orch_inject` CLI command, using the existing `strip_artifact_path_prefix()` function before passing the chunk identifier to the orchestrator client. The normalization happens at the CLI layer (not the API layer) because the CLI is the user-facing interface where path flexibility matters.

Following TDD per docs/trunk/TESTING_PHILOSOPHY.md, we'll write failing tests first that verify the path normalization behavior, then add the single line of implementation to make them pass.

## Subsystem Considerations

No subsystems are directly relevant to this work. This is a narrow CLI usability improvement that uses an existing utility function.

## Sequence

### Step 1: Write failing tests for path normalization

Add a new test class `TestOrchInjectPathNormalization` to `tests/test_chunk_validate_inject.py` that verifies the path normalization behavior. Tests should cover:

1. Full path with trailing slash: `docs/chunks/my_feature/` → works
2. Full path without trailing slash: `docs/chunks/my_feature` → works
3. Short prefix path: `chunks/my_feature` → works
4. Short name (existing behavior): `my_feature` → works

Since the orchestrator daemon is complex to test (requires starting a server), use mocking to verify that the correct normalized chunk name is passed to the client. The existing `test_chunk_validate_inject.py` tests the validation function directly, which is the appropriate level for our tests.

Actually, since validation happens in `Chunks.validate_chunk_injectable()` which already receives the chunk ID and uses `resolve_chunk_id()`, the cleanest approach is to test the `strip_artifact_path_prefix()` function directly for chunk paths to verify the normalization behavior, then verify the integration at the CLI level.

**Test approach**: Write unit tests that call `strip_artifact_path_prefix()` with CHUNK type for various path formats, verifying the output is the short name. Then write a minimal CLI integration test that verifies `ve orch inject` with a full path doesn't error with "chunk not found" (it will error with "daemon not running" which proves the normalization worked).

Location: `tests/test_chunk_validate_inject.py` (add new test class)

### Step 2: Add path normalization to orch_inject CLI command

Add a single line to the `orch_inject` function in `src/ve.py` that normalizes the chunk argument before passing it to the client:

```python
chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)
```

This follows the exact same pattern used by 10+ other commands in the file.

Location: `src/ve.py` around line 2031 (after the imports, before building the request body)

### Step 3: Run tests and verify

Run the test suite to verify:
1. New path normalization tests pass
2. Existing `test_chunk_validate_inject.py` tests still pass
3. No regressions in other orchestrator tests

### Step 4: Manual verification

Test the behavior manually:
- `ve orch inject docs/chunks/some_chunk/` should work
- `ve orch inject chunks/some_chunk` should work
- `ve orch inject some_chunk` should work (existing behavior preserved)

## Dependencies

None. The `strip_artifact_path_prefix()` function already exists in `src/external_refs.py` and is already imported in `src/ve.py`.

## Risks and Open Questions

**Low risk**: This is a well-established pattern in the codebase. The main consideration is ensuring tests adequately cover the behavior without requiring the orchestrator daemon to be running.

**Testing without daemon**: The orchestrator inject command requires a running daemon. Tests will need to either:
1. Test the path normalization function directly (unit test level)
2. Mock the client to verify the normalized value is passed
3. Accept that the CLI will fail with "daemon not running" rather than "chunk not found" as proof normalization worked

Option 1 is cleanest and aligns with TESTING_PHILOSOPHY.md's preference for testing behavior at the appropriate boundary.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->