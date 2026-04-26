---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- src/orchestrator/scheduler.py
- tests/test_orchestrator_worktree.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/worktree.py#WorktreeManager::commit_changes
    implements: "Mechanical commit: stages all changes and commits with standard message"
  - ref: src/orchestrator/worktree.py#WorktreeManager::finalize_work_unit
    implements: "Delegates to commit_changes as part of finalization lifecycle"
  - ref: tests/test_orchestrator_worktree_operations.py#TestCommitChanges
    implements: "Unit tests for commit_changes method"
  - ref: tests/test_orchestrator_scheduler_results.py#TestMechanicalCommit
    implements: "Unit tests for mechanical commit in scheduler"
narrative: null
investigation: null
subsystems: []
created_after: ["orch_attention_queue", "orch_conflict_oracle", "orch_agent_skills", "orch_question_forward"]
---

# Chunk Goal

## Minor Goal

The orchestrator commits chunk changes mechanically, without an agent. After
the COMPLETE phase succeeds and uncommitted changes are detected, the scheduler
invokes `WorktreeManager.commit_changes`, which runs git directly in the
worktree:

```bash
git add -A
git commit -m "feat: chunk <chunk_name>"
```

Because no agent decides where to run these commands, the commit cannot escape
the worktree sandbox. This path replaces the prior agent-driven `run_commit`
flow that relied on the `/chunk-commit` skill.

## Success Criteria

- **Mechanical commit in scheduler**: Replace the `agent_runner.run_commit()`
  call in `src/orchestrator/scheduler.py` with direct subprocess calls to git
  - Run `git add -A` in the worktree directory
  - Run `git commit -m "feat: chunk {chunk}"` in the worktree directory
  - Handle commit failure gracefully (mark NEEDS_ATTENTION)

- **No agent involvement**: The commit operation must not use `ClaudeAgent` or
  any agent-based execution. Pure subprocess/git operations only.

- **Worktree isolation**: Git commands must run with `cwd=worktree_path` to
  ensure they operate on the worktree, not the host repo

- **Error handling**: If `git commit` fails (e.g., nothing to commit after
  `git add -A`), log appropriately and proceed to merge phase

- **Logging**: Log the commit operation to the orchestrator log (not to an
  agent log file since there's no agent)

- **Test coverage**:
  - Unit test verifying mechanical commit runs git commands in worktree
  - Unit test verifying commit message format matches `feat: chunk <name>`
  - Unit test verifying failure handling marks NEEDS_ATTENTION

- **Cleanup**: Remove or deprecate `AgentRunner.run_commit()` method if no
  longer needed, or keep it for potential manual use cases

- **No regressions**: All existing orchestrator tests pass