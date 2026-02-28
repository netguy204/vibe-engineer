# Implementation Plan

## Approach

This chunk implements a safety check for branch deletion when deleting work units via the orchestrator API. The motivating incident (documented in `docs/investigations/orch_stuck_recovery/OVERVIEW.md`) showed that force-deleting branches with unmerged commits caused data loss that required `git reflog` archaeology to recover.

**Strategy:**

1. **Pre-delete merge verification**: Before deleting a branch, count commits on the `orch/<chunk>` branch that aren't reachable from the base branch. If commits exist, refuse deletion unless `force=True`.

2. **Safe delete by default**: Change `_remove_single_repo_worktree` to use `git branch -d` (which refuses to delete unmerged branches) instead of `git branch -D` (force delete). Only use `-D` when force is explicitly requested.

3. **API surface**: Add `force` query parameter to `DELETE /work-units/{chunk}` endpoint and `--force` CLI flag to `ve orch work-unit delete`.

4. **Clear error messaging**: When blocking deletion, report the number of unmerged commits to help operators understand why the delete was refused.

**Existing patterns leveraged:**
- The normal finalization path (`finalize_work_unit`) already uses `git branch -d` (safe delete)
- The `_load_base_branch` method can retrieve the persisted base branch for comparison
- Error responses follow the existing `error_response()` pattern in `api/work_units.py`

**Testing approach (per TESTING_PHILOSOPHY.md):**
- Test the core behavior at boundaries: merged branch, unmerged branch, unmerged + force
- Use real git repositories in tests (existing pattern in `test_orchestrator_api.py`)
- Verify error messages contain actionable information

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a safety mechanism for the orchestrator's branch deletion logic. The existing subsystem patterns are followed.

## Sequence

### Step 1: Add `has_unmerged_commits` method to WorktreeManager

Add a new public method to `WorktreeManager` that checks whether a branch has commits not reachable from the base branch.

Location: `src/orchestrator/worktree.py`

```python
def has_unmerged_commits(self, chunk: str) -> tuple[bool, int]:
    """Check if a chunk's branch has unmerged commits.

    Returns:
        Tuple of (has_unmerged, commit_count)
    """
```

Implementation:
- Load the persisted base branch via `_load_base_branch(chunk)` (falling back to `self._base_branch`)
- Run `git rev-list {base_branch}..orch/{chunk} --count`
- Return `(count > 0, count)`

### Step 2: Add `force` parameter to `remove_worktree` and `_remove_single_repo_worktree`

Modify these methods to accept a `force` parameter that controls branch deletion behavior.

Location: `src/orchestrator/worktree.py`

Changes:
- Add `force: bool = False` parameter to `remove_worktree()`
- Add `force: bool = False` parameter to `_remove_single_repo_worktree()`
- Change line 665-670 from `git branch -D` to `git branch -d` by default
- Only use `git branch -D` when `force=True`
- Also update `_remove_task_context_worktrees()` for consistency (lines 700-707)

### Step 3: Update `delete_work_unit_endpoint` to check for unmerged commits

Modify the delete endpoint to check for unmerged commits before deleting.

Location: `src/orchestrator/api/work_units.py`

Changes:
- Parse `force` query parameter from request
- Before calling `remove_worktree()`, check `has_unmerged_commits()`
- If unmerged commits exist and `force=False`, return error response with commit count
- Pass `force` parameter to `remove_worktree()`

### Step 4: Update client `delete_work_unit` to support force parameter

Add `force` parameter to the client method.

Location: `src/orchestrator/client.py`

Changes:
- Add `force: bool = False` parameter to `delete_work_unit()`
- Pass `force` as query parameter: `params={"force": "true"}` if force else `None`

### Step 5: Update CLI `work-unit delete` to support --force flag

Add `--force` flag to the CLI command.

Location: `src/cli/orch.py`

Changes:
- Add `@click.option("--force", is_flag=True, help="Force delete even if branch has unmerged commits")`
- Pass `force` to `client.delete_work_unit()`

### Step 6: Write tests for safe branch deletion

Add tests to verify the safety behavior.

Location: `tests/test_orchestrator_api.py` (new test class)

Tests to add:
1. `test_delete_with_merged_branch_succeeds` - Delete works when branch is fully merged
2. `test_delete_with_unmerged_branch_fails` - Delete refused when branch has unmerged commits
3. `test_delete_with_unmerged_branch_force_succeeds` - Delete works with `force=True`
4. `test_delete_error_includes_commit_count` - Error message includes number of unmerged commits

Tests for worktree methods (in `tests/test_orchestrator_worktree.py` or similar):
5. `test_has_unmerged_commits_detects_unmerged` - Method correctly detects unmerged commits
6. `test_has_unmerged_commits_returns_zero_when_merged` - Method returns (False, 0) for merged branch
7. `test_remove_worktree_uses_safe_delete_by_default` - Verifies `-d` is used, not `-D`

### Step 7: Update documentation

Update the orchestrator documentation template to reflect the new behavior.

Location: `src/templates/trunk/ORCHESTRATOR.md.jinja2`

Changes:
- Update the `ve orch work-unit delete` command description
- Add note about the safety check and `--force` flag

## Risks and Open Questions

1. **Squash merge false positives**: When using squash merges, `git branch -d` may refuse to delete even when the code is on main (because commit SHAs differ). The investigation noted this but accepted it as an acceptable trade-off for safety. The `--force` flag provides an escape hatch.

2. **Base branch detection**: If the base_branch file doesn't exist (legacy worktrees created before `orch_merge_safety` chunk), we fall back to `self._base_branch`. This may be stale if the manager was created before branch changes, but it's the best available fallback.

3. **Multi-repo mode**: The current scope focuses on single-repo mode. Multi-repo mode (`_remove_task_context_worktrees`) also uses `-D` and should be updated for consistency, but the investigation incident was single-repo.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->