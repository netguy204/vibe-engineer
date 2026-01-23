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
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Calls commit_changes instead of agent-driven commit after COMPLETE phase"
  - ref: tests/test_orchestrator_worktree.py#TestCommitChanges
    implements: "Unit tests for commit_changes method"
  - ref: tests/test_orchestrator_scheduler.py#TestMechanicalCommit
    implements: "Unit tests for mechanical commit in scheduler"
narrative: null
investigation: null
subsystems: []
created_after: ["orch_attention_queue", "orch_conflict_oracle", "orch_agent_skills", "orch_question_forward"]
---

# Chunk Goal

## Minor Goal

Replace the agent-driven commit phase with a mechanical commit. Currently, when
the orchestrator detects uncommitted changes after the COMPLETE phase, it runs
`agent_runner.run_commit()` which launches an agent with the `/chunk-commit`
skill. This agent can escape the worktree sandbox (as demonstrated when the
`orch_sandbox_enforcement` chunk's agent ran `cd /host/repo && git commit`,
committing to main instead of the worktree branch).

The fix is to eliminate the agent entirely for commits. After COMPLETE phase
succeeds and uncommitted changes are detected, mechanically run git commands
directly in the worktree:

```bash
git add -A
git commit -m "feat: chunk <chunk_name>"
```

This is simpler, faster, and cannot escape the sandbox because there's no agent
making decisions about where to run commands.

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