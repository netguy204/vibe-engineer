<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the `WorktreeManager` class to create symlinks for task-level configuration files (`.ve-task.yaml`, `CLAUDE.md`, `.claude/`) when creating worktrees in task context mode.

**Core strategy:**
1. After creating worktrees for each repo under `work/`, create symlinks in the `work/` directory that point to task-level configuration files
2. Symlinks point to the task directory (parent of `.ve/`), not the worktree content
3. The symlinks are created immediately after worktree creation in `_create_task_context_worktrees()`
4. Cleanup removes these symlinks when worktrees are removed

**Why symlinks in `work/` directory:**
- The agent's working directory is `work/` (not individual repo worktrees)
- The agent needs to see task-level `CLAUDE.md` for task-specific instructions
- The agent needs to see `.ve-task.yaml` to detect task context
- The `.claude/` directory provides task-level slash commands
- These files live at the task directory level (e.g., `auth-token-work/CLAUDE.md`)
- Without symlinks, agents would only see repo-specific `CLAUDE.md` files inside each worktree

**Single-repo mode unchanged:**
- When not in task context, the existing `worktree/` structure is used
- Agents run directly in the worktree which has its own `CLAUDE.md`
- No symlinks needed

**Reference:** This chunk implements findings from the `orch_task_context` investigation (docs/investigations/orch_task_context/OVERVIEW.md).

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS part of the orchestrator subsystem's worktree management. Extends `WorktreeManager` with symlink setup for task context agent environment. The subsystem is DOCUMENTED status, so this is new functionality rather than fixing deviations.

## Sequence

### Step 1: Add tests for symlink creation in task context (TDD red phase)

Write failing tests for the symlink behavior before implementing.

Location: `tests/test_orchestrator_worktree.py`

Add a new test class `TestTaskContextSymlinks`:

```python
class TestTaskContextSymlinks:
    """Tests for symlink creation in task context mode."""

    @pytest.fixture
    def task_directory_with_config(self, tmp_path):
        """Create a task directory with CLAUDE.md and .claude/ for testing."""
        task_dir, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a"],
        )
        # Create task-level CLAUDE.md
        (task_dir / "CLAUDE.md").write_text("# Task-level guidance\n")
        # Create task-level .claude/ directory with a command
        (task_dir / ".claude").mkdir()
        (task_dir / ".claude" / "test-command.md").write_text("# Test command\n")
        return {
            "task_dir": task_dir,
            "external": external,
            "project_a": projects[0],
        }

    def test_creates_ve_task_yaml_symlink(self, task_directory_with_config):
        """Creates symlink to .ve-task.yaml in work/ directory."""

    def test_creates_claude_md_symlink(self, task_directory_with_config):
        """Creates symlink to CLAUDE.md in work/ directory."""

    def test_creates_claude_dir_symlink(self, task_directory_with_config):
        """Creates symlink to .claude/ directory in work/ directory."""

    def test_symlinks_point_to_task_directory(self, task_directory_with_config):
        """Symlinks resolve to task directory files, not worktree files."""

    def test_symlinks_removed_on_worktree_cleanup(self, task_directory_with_config):
        """Symlinks are cleaned up when worktree is removed."""

    def test_single_repo_mode_no_symlinks(self, git_repo):
        """No symlinks created in single-repo mode."""

    def test_missing_claude_md_skipped(self, task_directory_with_config):
        """Missing CLAUDE.md doesn't cause error, just skips that symlink."""
```

### Step 2: Add helper method to determine task directory from project_dir

Add a method to `WorktreeManager` that resolves the task directory from the project_dir when in task context.

Location: `src/orchestrator/worktree.py`

```python
def _get_task_directory(self) -> Optional[Path]:
    """Get the task directory if in task context mode.

    In task context, task_info.root_dir is the task directory.
    Returns None if not in task context.
    """
    if self.task_info and self.task_info.is_task_context:
        return self.task_info.root_dir
    return None
```

### Step 3: Implement symlink creation in task context worktrees

Modify `_create_task_context_worktrees()` to create symlinks after creating repo worktrees.

Location: `src/orchestrator/worktree.py`

Add a new private method:

```python
# Chunk: docs/chunks/orch_task_agent_env - Task context agent environment symlinks
def _setup_agent_environment_symlinks(self, work_dir: Path) -> None:
    """Create symlinks to task-level configuration in work/ directory.

    Creates symlinks for:
    - .ve-task.yaml -> task_directory/.ve-task.yaml
    - CLAUDE.md -> task_directory/CLAUDE.md
    - .claude/ -> task_directory/.claude/

    Missing source files are skipped (not an error).

    Args:
        work_dir: The work/ directory where symlinks should be created
    """
    task_dir = self._get_task_directory()
    if task_dir is None:
        return

    symlink_targets = [
        (".ve-task.yaml", task_dir / ".ve-task.yaml"),
        ("CLAUDE.md", task_dir / "CLAUDE.md"),
        (".claude", task_dir / ".claude"),
    ]

    for link_name, target_path in symlink_targets:
        link_path = work_dir / link_name
        if target_path.exists() and not link_path.exists():
            link_path.symlink_to(target_path)
```

Modify `_create_task_context_worktrees()` to call this method:

```python
def _create_task_context_worktrees(self, chunk: str, repo_paths: list[Path]) -> Path:
    """Create worktrees for multiple repos in task context mode."""
    work_dir = self.get_work_directory(chunk)
    work_dir.mkdir(parents=True, exist_ok=True)
    branch = self.get_branch_name(chunk)

    for repo_path in repo_paths:
        # ... existing worktree creation code ...

    # Set up agent environment symlinks
    self._setup_agent_environment_symlinks(work_dir)

    return work_dir
```

### Step 4: Implement symlink cleanup

Modify `_remove_task_context_worktrees()` to remove symlinks before removing the work directory.

Location: `src/orchestrator/worktree.py`

Add a new private method:

```python
# Chunk: docs/chunks/orch_task_agent_env - Task context agent environment symlinks
def _cleanup_agent_environment_symlinks(self, work_dir: Path) -> None:
    """Remove symlinks from work/ directory.

    Args:
        work_dir: The work/ directory containing symlinks
    """
    symlink_names = [".ve-task.yaml", "CLAUDE.md", ".claude"]

    for link_name in symlink_names:
        link_path = work_dir / link_name
        if link_path.is_symlink():
            link_path.unlink()
```

Modify `_remove_task_context_worktrees()` to call this before shutil.rmtree:

```python
def _remove_task_context_worktrees(
    self, chunk: str, remove_branch: bool, repo_paths: list[Path]
) -> None:
    """Remove worktrees for multiple repos in task context mode."""
    work_dir = self.get_work_directory(chunk)
    # ... existing worktree removal code ...

    # Clean up symlinks before removing work directory
    if work_dir.exists():
        self._cleanup_agent_environment_symlinks(work_dir)
        shutil.rmtree(work_dir, ignore_errors=True)
```

### Step 5: Run tests and verify

Run the new tests to ensure:
1. Symlinks are created correctly in task context
2. Symlinks point to the correct task directory files
3. Symlinks are cleaned up on worktree removal
4. Single-repo mode is unchanged

```bash
uv run pytest tests/test_orchestrator_worktree.py::TestTaskContextSymlinks -v
```

Also run the full worktree test suite to verify no regressions:

```bash
uv run pytest tests/test_orchestrator_worktree.py -v
```

### Step 6: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter with the files touched:
- `src/orchestrator/worktree.py`
- `tests/test_orchestrator_worktree.py`

## Dependencies

- **orch_task_worktrees**: This chunk depends on the task context worktree structure created by `orch_task_worktrees`. That chunk introduced `_create_task_context_worktrees()` and the `work/` directory structure. This chunk extends that functionality with symlinks.

- **orch_task_detection**: This chunk uses `TaskContextInfo` which was introduced by `orch_task_detection`. The `WorktreeManager` already accepts `task_info` parameter.

No external library dependencies - uses only Python's `pathlib.Path.symlink_to()`.

## Risks and Open Questions

1. **Relative vs absolute symlinks**: Using `symlink_to(target_path)` creates an absolute symlink. This is fine for local worktrees but could be an issue if worktrees are moved. **Mitigation**: Worktrees are always created fresh and not moved, so absolute symlinks are acceptable.

2. **Symlink permissions on Windows**: Windows symlinks may require elevated permissions or developer mode. **Mitigation**: The orchestrator is primarily used on macOS/Linux. Document Windows limitations if needed.

3. **Symlink resolution in git operations**: Git should ignore symlinks when staging/committing in the work directory (they point outside the repos). **Verification needed**: Confirm git doesn't try to add/track these symlinks in the worktree repos.

4. **Existing files in work/ directory**: If a file already exists at the symlink path (e.g., stale state from crash), symlink creation would fail. **Mitigation**: Check `not link_path.exists()` before creating symlink. The cleanup method removes symlinks properly.

5. **Agent detection of task context**: The agent needs to detect task context from the symlinked `.ve-task.yaml`. Since the symlink resolves to the real file, this should work transparently. **Verification needed**: Test that task context detection works from inside `work/` directory.

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