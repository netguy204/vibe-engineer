---
decision: APPROVE
summary: All success criteria satisfied - safe branch deletion prevents data loss with comprehensive test coverage, clear error messaging, and proper documentation updates.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `delete_work_unit_endpoint` checks for unmerged commits before deleting the branch (via `git rev-list main..orch/<chunk> --count` or equivalent)

- **Status**: satisfied
- **Evidence**: `api/work_units.py:266-275` - Creates WorktreeManager and calls `has_unmerged_commits(chunk)` before proceeding with deletion. The `has_unmerged_commits` method in `worktree.py:804-844` uses `git rev-list {base_branch}..{branch} --count` to detect unmerged commits.

### Criterion 2: If unmerged commits exist, the delete is refused with a clear error message showing the commit count

- **Status**: satisfied
- **Evidence**: `api/work_units.py:270-275` - Returns 409 Conflict with error message: `f"Branch has {commit_count} unmerged commit(s). Use force=true to delete anyway, or merge changes first."`. Test `test_delete_error_includes_commit_count` verifies "3 unmerged commit(s)" appears in error.

### Criterion 3: A `--force` flag (CLI) / `force` query param (API) overrides the safety check when the operator explicitly intends to discard the work

- **Status**: satisfied
- **Evidence**:
  - API: `work_units.py:259-261` parses `force` query param
  - CLI: `orch.py:312` adds `--force` flag to `work_unit_delete` command
  - Client: `client.py:226-243` accepts `force: bool = False` parameter and passes it as query param
  - When `force=True`, the safety check is bypassed (`work_units.py:270` only refuses if `not force`)

### Criterion 4: `_remove_single_repo_worktree` uses `git branch -d` (safe delete) by default instead of `git branch -D`

- **Status**: satisfied
- **Evidence**: `worktree.py:674-676` - `delete_flag = "-D" if force else "-d"` with `force: bool = False` default parameter in method signature at line 649.

### Criterion 5: Force delete (`-D`) is only used when the force flag is set

- **Status**: satisfied
- **Evidence**: `worktree.py:675` - `-D` only used when `force=True`. Also updated `_remove_task_context_worktrees` at line 717 for consistency in multi-repo mode.

### Criterion 6: Tests cover: delete with merged branch succeeds, delete with unmerged branch fails, delete with unmerged branch + force succeeds

- **Status**: satisfied
- **Evidence**: `tests/test_orchestrator_api.py:327-473` contains:
  - `test_delete_with_merged_branch_succeeds` (line 430)
  - `test_delete_with_unmerged_branch_fails` (line 366)
  - `test_delete_with_unmerged_branch_force_succeeds` (line 399)
  - `test_delete_error_includes_commit_count` (line 447)

  Additionally, `tests/test_orchestrator_worktree_core.py:354-414` has unit tests for `has_unmerged_commits` method.

### Criterion 7: Existing orchestrator tests pass

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/test_orchestrator_api.py -v` shows 80/80 tests passing. Broader test run shows 845 passed with 1 unrelated failure in daemon process detection test (not modified by this chunk).

## Documentation Updates

- **ORCHESTRATOR.md.jinja2** updated with "Deleting Work Units" section explaining safe delete behavior, error messages, `--force` usage, and alternatives (lines 85-107).
- Code backreference comments added: `worktree.py:647,684,803`, `work_units.py:246`, `client.py:225`, `orch.py:309`.

## Subsystem Invariants

- **orchestrator subsystem**: Implementation follows existing patterns - CLI is thin wrapper, business logic in API/worktree layer, proper error responses via `error_response()` helper.
