# Implementation Plan

## Approach

Modify `update_working_tree_if_on_branch` in `src/orchestrator/merge.py` to check for uncommitted changes before running any working tree modification commands. This follows a simple guard pattern:

1. Check if working tree is dirty (via `git status --porcelain`)
2. If dirty, log a warning and return early without modifying working tree
3. If clean, proceed with existing behavior (`git reset --mixed HEAD` + `git checkout -- .`)

The fix is encapsulated entirely within `update_working_tree_if_on_branch`, requiring no changes to its three call sites (`merge_without_checkout`, `fast_forward_merge`/fast-forward path within `merge_without_checkout`, and `merge_via_index`). The function already returns `None` and is called for side effects only, so returning early is safe.

Per TESTING_PHILOSOPHY.md, tests are written first (TDD) and verify semantically meaningful behavior:
- Dirty working tree: function returns early, no `git checkout -- .` executed, warning logged
- Clean working tree: function updates files as before

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS part of the orchestrator subsystem, specifically the merge module's working tree safety. The subsystem is DOCUMENTED status, so no opportunistic deviation fixes are required.

## Sequence

### Step 1: Write failing tests for dirty working tree path

Add tests in `tests/test_orchestrator_merge.py` (new file) that verify:
- Given uncommitted changes exist, `update_working_tree_if_on_branch` does not run `git checkout -- .`
- Given uncommitted changes exist, a warning is logged indicating the working tree is behind

Test setup pattern follows existing `test_orchestrator_worktree_persistence.py`:
- Create a git repo fixture
- Make uncommitted changes (staged or unstaged)
- Call `update_working_tree_if_on_branch`
- Assert: uncommitted changes still exist (proves `git checkout -- .` was not run)

Location: `tests/test_orchestrator_merge.py`

### Step 2: Write failing tests for clean working tree path

Add tests verifying existing behavior is preserved:
- Given a clean working tree and a branch with new commits, `update_working_tree_if_on_branch` updates files in working tree

Test setup:
- Create a git repo
- Update ref via `git update-ref` (simulating what merge functions do)
- Call `update_working_tree_if_on_branch`
- Assert: working tree files match the new commit

Location: `tests/test_orchestrator_merge.py`

### Step 3: Implement dirty working tree detection

Modify `update_working_tree_if_on_branch` in `src/orchestrator/merge.py`:

1. After determining we're on the target branch, run `git status --porcelain` to detect uncommitted changes
2. `git status --porcelain` outputs nothing if clean, outputs one line per changed file if dirty
3. If output is non-empty, the working tree is dirty

Add a check before the `git reset --mixed HEAD` line.

Location: `src/orchestrator/merge.py`, function `update_working_tree_if_on_branch`

### Step 4: Implement early return with warning

When dirty working tree is detected:
1. Import `logging` module (if not already imported)
2. Log a warning: "Working tree has uncommitted changes; skipping update. Your working tree is behind branch '{target_branch}'. Manually run 'git merge' or 'git rebase' to reconcile."
3. Return early (before `git reset --mixed HEAD`)

The warning clearly explains:
- What happened (skipped update)
- Why (uncommitted changes)
- What to do (manual reconciliation)

Location: `src/orchestrator/merge.py`, function `update_working_tree_if_on_branch`

### Step 5: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter `code_paths` field to include:
- `src/orchestrator/merge.py`
- `tests/test_orchestrator_merge.py`

Location: `docs/chunks/merge_safety/GOAL.md`

### Step 6: Run tests and verify

Run the test suite to verify:
- New tests pass
- Existing merge-related tests still pass (no regressions)
- The three call sites work correctly (merge_without_checkout ff path, merge_without_checkout merge path, merge_via_index)

Command: `uv run pytest tests/test_orchestrator_merge.py tests/test_orchestrator_worktree_persistence.py -v`

## Risks and Open Questions

1. **Staged vs unstaged changes**: `git status --porcelain` detects both staged and unstaged changes. This is the desired behavior per the goal ("uncommitted changes" = anything not committed), but worth confirming.

2. **Logging module**: The module doesn't currently import logging. Need to add `import logging` and get a module logger. This is a minimal addition consistent with Python best practices.

3. **Test isolation**: The `clean_git_environment` autouse fixture in conftest.py removes `GIT_*` environment variables, which is important for test isolation. The new tests should work correctly with this fixture.

## Deviations

*To be populated during implementation.*