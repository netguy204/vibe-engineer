---
decision: APPROVE
summary: All five success criteria satisfied — psutil-based process reaping with SIGTERM→SIGKILL is implemented correctly in _remove_worktree_from_repo, with full test coverage and no regressions in existing orchestrator tests.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `remove_worktree` kills child processes rooted in the worktree path before removing the directory

- **Status**: satisfied
- **Evidence**: `_reap_worktree_processes(worktree_path)` is called at the very top of `_remove_worktree_from_repo` (worktree.py:839), before `_unlock_worktree` and before `git worktree remove`. Processes are matched by cwd prefix or cmdline substring against the worktree path. The orchestrator's own PID is explicitly excluded.

### Criterion 2: SIGTERM is sent first with a grace period before SIGKILL

- **Status**: satisfied
- **Evidence**: worktree.py:810–829 — all candidates receive `SIGTERM`, then `time.sleep(5)` is called, then any process still `is_running()` receives `SIGKILL`. Each step is wrapped in `try/except (NoSuchProcess, AccessDenied)` to tolerate races.

### Criterion 3: Reaped processes are logged at WARNING level

- **Status**: satisfied
- **Evidence**: worktree.py:803–808 logs `"Reaping %d process(es) in worktree %s: PIDs %s"` at WARNING before SIGTERM. worktree.py:825–827 logs `"PID %d did not exit after SIGTERM; sent SIGKILL"` at WARNING per survivor. No log is emitted when no candidates are found (happy-path silence preserved).

### Criterion 4: Test covers the reap behavior (mock process discovery + kill)

- **Status**: satisfied
- **Evidence**: `TestReapWorktreeProcesses` in `tests/test_orchestrator_worktree.py` contains all 5 planned tests: SIGTERM→SIGKILL for survivors, SIGTERM-only for processes that exit, no-kill for out-of-worktree processes, no-log when candidate list is empty, and an integration test asserting `_reap_worktree_processes` is called before the directory is removed. All 5 pass.

### Criterion 5: Existing orchestrator tests pass

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` shows 999 passed, 1 failed. The single failure (`test_entity_fork_merge.py::TestForkEntity::test_fork_records_forked_from`) is in an unrelated entity-forking module (`EntityRepoMetadata.forked_from`) not touched by this chunk; it is a pre-existing failure unrelated to process reaping.
