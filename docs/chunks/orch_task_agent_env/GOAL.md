---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- tests/test_orchestrator_worktree.py
code_references:
  - ref: src/orchestrator/worktree.py#WorktreeManager::_get_task_directory
    implements: "Helper to resolve task directory from task_info for symlink creation"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_setup_agent_environment_symlinks
    implements: "Creates symlinks to task-level configuration (.ve-task.yaml, CLAUDE.md, .claude/) in work/ directory"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_cleanup_agent_environment_symlinks
    implements: "Removes symlinks during worktree cleanup"
  - ref: tests/test_orchestrator_worktree.py#TestTaskContextSymlinks
    implements: "Tests for symlink creation, resolution, and cleanup in task context mode"
narrative: null
investigation: orch_task_context
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
created_after:
- taskdir_subsystem_overlap
---

# Chunk Goal

## Minor Goal

Set up the agent environment in the `work/` directory with symlinks to task-level configuration files.

When an agent runs in a task context, it needs access to:
- `.ve-task.yaml` - so it knows it's in a task context
- `CLAUDE.md` - task-level agent guidance (different from individual repo versions)
- `.claude/` - task-level commands

These files exist at the task directory level and provide task-context-specific behavior. Symlinks ensure agents get the task-level instructions rather than repo-specific ones.

Target structure:
```
.ve/chunks/<chunk>/
  work/
    .ve-task.yaml        # symlink → task-directory/.ve-task.yaml
    CLAUDE.md            # symlink → task-directory/CLAUDE.md
    .claude/             # symlink → task-directory/.claude/
    external-repo/       # Worktree
    project-a/           # Worktree
  log/
```

## Success Criteria

- When creating worktrees in task context, symlinks are created for `.ve-task.yaml`, `CLAUDE.md`, and `.claude/`
- Symlinks point to task directory versions (parent of `.ve/`)
- Agent running from `work/` directory sees task-level configuration
- Symlinks are cleaned up when worktree is removed
- Single-repo mode unchanged (no symlinks needed, agent runs in worktree which has its own `CLAUDE.md`)