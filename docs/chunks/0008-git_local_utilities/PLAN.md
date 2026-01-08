<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements two git utility functions that operate on local repositories and worktrees. The implementation will use Python's `subprocess` module to invoke git commands, following the same pattern used throughout the codebase (simple, dependency-light utilities).

Per DEC-002 (git not assumed), these utilities are designed to work with worktrees within a task directory structure, where multiple repos are checked out locally. They deliberately avoid network operations—no fetching, no remote resolution.

The implementation follows test-driven development per TESTING_PHILOSOPHY.md:
1. Write failing tests first
2. Implement minimum code to make tests pass
3. Verify all success criteria are met

## Sequence

### Step 1: Write failing tests for get_current_sha

Create `tests/test_git_utils.py` with tests for `get_current_sha()`:

- Test successful SHA retrieval from a git repository
- Test error when path is not a git repository
- Test error when path does not exist
- Test that returned SHA is exactly 40 hex characters
- Test that function works with git worktrees (not just regular repos)

The tests will require creating temporary git repositories using `git init` and `git commit`.

Location: `tests/test_git_utils.py`

### Step 2: Implement get_current_sha

Create `src/git_utils.py` with the `get_current_sha(repo_path: Path) -> str` function:

- Use `git rev-parse HEAD` to get the current SHA
- Validate the path is a directory before running git
- Raise `ValueError` with clear message including the path if:
  - Path is not a git repository
  - Path does not exist
- Return the full 40-character SHA (no truncation)

Location: `src/git_utils.py`

### Step 3: Write failing tests for resolve_ref

Add tests for `resolve_ref()` to `tests/test_git_utils.py`:

- Test successful resolution of branch names (e.g., `main`, `feature/foo`)
- Test successful resolution of tag names (e.g., `v1.0.0`)
- Test successful resolution of symbolic refs (e.g., `HEAD`, `HEAD~1`)
- Test error when path is not a git repository
- Test error when ref does not exist
- Test that returned SHA is exactly 40 hex characters

The tests will extend the git repository fixtures to include branches and tags.

Location: `tests/test_git_utils.py`

### Step 4: Implement resolve_ref

Add `resolve_ref(repo_path: Path, ref: str) -> str` to `src/git_utils.py`:

- Use `git rev-parse <ref>` to resolve the ref to a SHA
- Validate the path is a directory before running git
- Raise `ValueError` with clear message including both path and ref if:
  - Path is not a git repository
  - Ref does not exist or cannot be resolved
- Return the full 40-character SHA

Location: `src/git_utils.py`

### Step 5: Add worktree-specific tests

Add tests that specifically validate worktree support:

- Create a git repository with a worktree
- Test `get_current_sha` works from the worktree
- Test `resolve_ref` works from the worktree
- Verify the functions return the correct SHA for the worktree's HEAD (which may differ from the main repo)

This ensures the functions work in the cross-repo task directory context described in the narrative.

Location: `tests/test_git_utils.py`

### Step 6: Verify all tests pass and success criteria are met

Run the full test suite to confirm:
- All new tests pass
- No regressions in existing tests
- Both functions work with regular repos and worktrees
- Error messages include path and ref information

## Dependencies

- **Chunk 0007 (schemas)**: Completed. Provides the models and task_utils that will eventually consume these git utilities.
- **External**: `git` must be available on the system PATH. No additional Python dependencies required.

## Risks and Open Questions

- **Git availability**: Tests will fail if git is not installed. This is acceptable since git is a fundamental assumption of the task directory workflow.
- **Windows compatibility**: `subprocess` calls to git should work on Windows, but path handling may need care. The existing codebase uses pathlib throughout, which handles this.
- **Detached HEAD state**: Both functions should work correctly when HEAD is detached (pointing directly to a SHA rather than a branch). This should be covered by `git rev-parse` behavior.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
