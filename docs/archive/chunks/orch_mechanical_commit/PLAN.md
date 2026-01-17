<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Replace the agent-driven commit in `scheduler.py` with a direct subprocess call
to git. The current flow:

1. `scheduler.py:601` detects uncommitted changes via `worktree_manager.has_uncommitted_changes()`
2. `scheduler.py:612` calls `agent_runner.run_commit()` which launches an agent
3. Agent runs `/chunk-commit` skill, which can escape sandbox

New flow:

1. Same detection of uncommitted changes
2. Run `git add -A` directly in worktree via subprocess
3. Run `git commit -m "feat: chunk <name>"` directly in worktree via subprocess
4. Handle failure gracefully (log and proceed to merge)

The mechanical commit will be a new method on `WorktreeManager` since it already
has `has_uncommitted_changes()` and manages worktree paths. This keeps git
operations grouped together.

Files to modify:
- `src/orchestrator/worktree.py` - Add `commit_changes()` method
- `src/orchestrator/scheduler.py` - Replace `agent_runner.run_commit()` with `worktree_manager.commit_changes()`
- `tests/test_orchestrator_worktree.py` - Add tests for `commit_changes()`
- `tests/test_orchestrator_scheduler.py` - Update mocks for new commit approach

## Subsystem Considerations

No subsystems are relevant to this chunk.

## Sequence

### Step 1: Add `commit_changes()` method to WorktreeManager

Location: `src/orchestrator/worktree.py`

Add a new method that performs the mechanical commit:

```python
def commit_changes(self, chunk: str) -> bool:
    """Commit all changes in a worktree with a standard message.

    Args:
        chunk: Chunk name

    Returns:
        True if commit succeeded, False if nothing to commit or error
    """
    worktree_path = self.get_worktree_path(chunk)

    # Stage all changes
    subprocess.run(["git", "add", "-A"], cwd=worktree_path, check=True)

    # Commit with standard message
    result = subprocess.run(
        ["git", "commit", "-m", f"feat: chunk {chunk}"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    # Return False if nothing to commit (exit code 1 with "nothing to commit")
    if result.returncode != 0:
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            return False
        raise RuntimeError(f"git commit failed: {result.stderr}")

    return True
```

### Step 2: Update scheduler to use mechanical commit

Location: `src/orchestrator/scheduler.py`

Replace the `agent_runner.run_commit()` call (lines 605-626) with:

```python
if self.worktree_manager.has_uncommitted_changes(chunk):
    logger.info(f"Uncommitted changes detected for {chunk}, committing")
    try:
        committed = self.worktree_manager.commit_changes(chunk)
        if committed:
            logger.info(f"Committed changes for {chunk}")
        else:
            logger.info(f"No changes to commit for {chunk}")
    except Exception as e:
        logger.error(f"Error committing changes for {chunk}: {e}")
        await self._mark_needs_attention(work_unit, f"Commit error: {e}")
        return
```

Remove the imports/usage of `create_log_callback` for the commit phase since
there's no agent log to write to.

### Step 3: Add tests for `commit_changes()`

Location: `tests/test_orchestrator_worktree.py`

Add a new test class:

```python
class TestCommitChanges:
    """Tests for WorktreeManager.commit_changes()"""

    def test_commit_changes_success(self, ...):
        """Commits staged changes with correct message format."""

    def test_commit_changes_nothing_to_commit(self, ...):
        """Returns False when nothing to commit."""

    def test_commit_changes_error(self, ...):
        """Raises on git error."""
```

### Step 4: Update scheduler tests

Location: `tests/test_orchestrator_scheduler.py`

Update the mock setup to use `worktree_manager.commit_changes` instead of
`agent_runner.run_commit`. The test at line 60 currently mocks `run_commit`.

### Step 5: Run tests and verify

Run the full test suite to ensure no regressions:

```bash
uv run pytest tests/test_orchestrator_worktree.py tests/test_orchestrator_scheduler.py -v
```

### Step 6: Consider cleanup of `run_commit`

Decide whether to remove `AgentRunner.run_commit()`. Check if it's used anywhere
else. If not, it can be removed. If there's a use case for manual agent-driven
commits, keep it but add a deprecation note.

## Dependencies

None. This chunk modifies existing orchestrator code with no new dependencies.

## Risks and Open Questions

- **Commit message format**: Using `feat: chunk <name>` is simple but may not
  capture the nature of the work. This is intentional - the chunk name provides
  context, and detailed commit messages are less important in worktree branches
  that get merged to main anyway.

- **`run_commit` removal**: If `AgentRunner.run_commit()` is used elsewhere or
  has value for manual debugging, we should keep it. Check usage before removing.

## Deviations

<!-- Populated during implementation -->