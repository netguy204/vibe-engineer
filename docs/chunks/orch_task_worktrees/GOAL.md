---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- tests/test_orchestrator_worktree_operations.py
- tests/test_orchestrator_worktree_persistence.py
code_references:
  - ref: src/orchestrator/worktree.py#WorktreeManager::get_work_directory
    implements: "Get work directory path for task context mode"
  - ref: src/orchestrator/worktree.py#WorktreeManager::is_task_context
    implements: "Detect whether chunk uses multi-repo task context structure"
  - ref: src/orchestrator/worktree.py#WorktreeManager::create_worktree
    implements: "Extended create_worktree with repo_paths for task context"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_create_task_context_worktrees
    implements: "Create worktrees for multiple repos under work/<repo-name>/"
  - ref: src/orchestrator/worktree.py#WorktreeManager::remove_worktree
    implements: "Extended remove_worktree with repo_paths for task context"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_remove_task_context_worktrees
    implements: "Remove worktrees for multiple repos in task context"
  - ref: src/orchestrator/worktree.py#WorktreeManager::merge_to_base
    implements: "Extended merge_to_base with repo_paths for task context"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_merge_to_base_multi_repo
    implements: "Merge chunk branch to base in each repository"
  - ref: src/orchestrator/worktree.py#WorktreeManager::has_changes
    implements: "Extended has_changes returning dict for multi-repo"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_has_changes_multi_repo
    implements: "Check changes per repository in task context"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_branch_exists_in_repo
    implements: "Check if branch exists in specific repository"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_get_repo_current_branch
    implements: "Get current branch of a specific repository"
  - ref: tests/test_orchestrator_worktree_operations.py#TestMultiRepoWorktreeCreation
    implements: "Tests for multi-repo worktree creation"
  - ref: tests/test_orchestrator_worktree_operations.py#TestMultiRepoWorktreeRemoval
    implements: "Tests for multi-repo worktree removal"
  - ref: tests/test_orchestrator_worktree_operations.py#TestMultiRepoMerge
    implements: "Tests for multi-repo merge operations"
  - ref: tests/test_orchestrator_worktree_persistence.py#TestTaskContextDetection
    implements: "Tests for task context detection"
narrative: null
investigation: orch_task_context
subsystems: []
friction_entries: []
bug_type: null
created_after:
- taskdir_subsystem_overlap
---

# Chunk Goal

## Minor Goal

Extend `WorktreeManager` to support task contexts by creating coordinated worktrees for multiple repositories under a shared `work/` directory.

Currently the orchestrator creates a single worktree per work unit in `.ve/chunks/<chunk>/worktree/`. In a task context, chunks span multiple repos (external artifacts repo + one or more project repos), requiring coordinated worktrees that maintain isolation while enabling the agent to work across all affected repos.

This chunk implements the core worktree structure:
```
.ve/chunks/<chunk>/
  work/
    external-repo/        # Worktree @ orch/<chunk>
    project-a/            # Worktree @ orch/<chunk>
  log/
```

## Success Criteria

- `WorktreeManager.create_worktree()` accepts an optional list of repo paths (for task context) or defaults to single-repo behavior
- For task contexts, creates worktrees for each specified repo under `work/<repo-name>/`
- Each worktree is on branch `orch/<chunk>` in its respective repo
- `WorktreeManager.remove_worktree()` cleans up all coordinated worktrees
- `WorktreeManager.merge_to_base()` merges in each repo independently
- Existing single-repo orchestrator behavior unchanged when not in task context
- Tests cover both single-repo and multi-repo worktree scenarios