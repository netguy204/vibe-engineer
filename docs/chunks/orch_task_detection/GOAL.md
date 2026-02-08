---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/models.py
- src/orchestrator/daemon.py
- src/orchestrator/scheduler.py
- src/orchestrator/state.py
- src/orchestrator/worktree.py
- src/ve.py
- tests/test_orch_task_context.py
code_references:
  - ref: src/orchestrator/models.py#TaskContextInfo
    implements: "Task context detection data model with is_task_context, root_dir, external_repo, project_paths fields"
  - ref: src/orchestrator/models.py#detect_task_context
    implements: "Detection logic for .ve-task.yaml to determine task vs single-repo mode"
  - ref: src/orchestrator/models.py#get_chunk_location
    implements: "Chunk directory resolution based on task context (external repo vs local docs/chunks)"
  - ref: src/orchestrator/models.py#get_chunk_dependents
    implements: "Parse chunk GOAL.md frontmatter to extract dependents field"
  - ref: src/orchestrator/models.py#resolve_affected_repos
    implements: "Map chunk dependents to filesystem paths for multi-repo worktree creation"
  - ref: src/orchestrator/daemon.py#start_daemon
    implements: "Daemon startup with task context detection, .ve/ placement at root_dir level"
  - ref: src/orchestrator/daemon.py#_run_daemon_async
    implements: "Async daemon runner with task_info parameter for scheduler creation"
  - ref: src/orchestrator/scheduler.py#create_scheduler
    implements: "Scheduler factory accepting task_info for multi-repo support"
  - ref: src/orchestrator/worktree.py#WorktreeManager
    implements: "Worktree manager with task_info support for multi-repo worktrees"
  - ref: src/orchestrator/worktree.py#WorktreeManager::create_worktree
    implements: "Worktree creation dispatching to single-repo or task context mode"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_create_task_context_worktrees
    implements: "Multi-repo worktree creation under .ve/chunks/<chunk>/work/<repo-name>/"
  - ref: src/orchestrator/api/common.py#get_chunk_directory
    implements: "Chunk directory resolution using task context for inject validation"
  - ref: src/orchestrator/api/scheduling.py#inject_endpoint
    implements: "Inject endpoint with task context chunk location resolution"
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

Add task context detection to the orchestrator daemon so it can run from a task directory with `.ve/` at that level.

Currently the orchestrator assumes it runs from a single git repository and places `.ve/` there. In a task context, the orchestrator should:
1. Detect `.ve-task.yaml` in the current directory (task directory mode)
2. Place `.ve/` at the task directory level, not inside any individual repo
3. Read chunk definitions from the external artifacts repo
4. Determine which project repos are affected by each chunk (via `dependents` field)

## Success Criteria

- Orchestrator detects task context by checking for `.ve-task.yaml`
- In task context: `.ve/` is created at task directory level
- In task context: chunks are read from external artifacts repo (per `.ve-task.yaml` config)
- In task context: work unit scheduling reads `dependents` from chunk GOAL.md to determine affected repos
- Single-repo mode (no `.ve-task.yaml`) unchanged
- `ve orch start` works from both task directories and single repos
- `ve orch inject <chunk>` correctly identifies chunk location in task context