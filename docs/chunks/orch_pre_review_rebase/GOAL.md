---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/models.py
- src/orchestrator/agent.py
- src/orchestrator/scheduler.py
- src/orchestrator/state.py
- src/cli/orch.py
- src/templates/commands/chunk-rebase.md.jinja2
- .claude/commands/chunk-rebase.md
- tests/test_orchestrator_scheduler.py
code_references:
- ref: src/orchestrator/models.py#WorkUnitPhase
  implements: REBASE phase between IMPLEMENT and REVIEW
- ref: src/orchestrator/log_streaming.py#PHASE_ORDER
  implements: REBASE phase in log file iteration order
- ref: src/orchestrator/agent.py#PHASE_SKILL_FILES
  implements: REBASE skill for pre-review trunk integration
- ref: src/orchestrator/scheduler.py#Scheduler::_handle_agent_result
  implements: Route REBASE phase completion to advance_phase
- ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
  implements: IMPLEMENT→REBASE→REVIEW phase progression
- ref: src/orchestrator/state.py#StateStore::_migrate_v13
  implements: Document REBASE as valid phase value in schema v13
- ref: src/templates/commands/chunk-rebase.md.jinja2
  implements: Agent prompt template for commit-merge-resolve-test workflow
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_exit_codes
- cli_help_text
- cli_json_output
---

# Chunk Goal

## Minor Goal

The orchestrator's phase progression includes a REBASE phase between IMPLEMENT and REVIEW. When parallel chunks run, branches diverge from main as other chunks merge in; the REBASE phase resolves that divergence before the REVIEW phase sees the code, so the reviewer evaluates clean, already-integrated changes rather than a stale snapshot.

**Phase progression:**
```
PLAN → IMPLEMENT → REBASE → REVIEW → COMPLETE → merge to main
```

**What the REBASE phase does:**

The REBASE phase is entirely agent-driven. The scheduler spawns an agent in the worktree with instructions to:

1. Commit any uncommitted work left by the IMPLEMENT phase (the implementer may have forgotten to stage files, or may have left work across multiple commits that should be consolidated)
2. Merge the current trunk (main) into the worktree branch
3. If conflicts arise, resolve them in light of the chunk's GOAL.md — keep the chunk's changes where they implement the goal, accept trunk changes elsewhere
4. Run the project's test suite to verify the integrated result
5. Report success or failure

On agent success, the phase advances to REVIEW. On unresolvable conflicts or test failure, the work unit is marked NEEDS_ATTENTION for operator help.

**Why agent-driven, not mechanical:**

The agent needs the full context of the chunk to handle the messy realities of the post-IMPLEMENT state. The IMPLEMENT phase may leave uncommitted files, may have produced multiple partial commits, or may have modified files that trunk also changed. A mechanical merge would lose the context needed to make the right decisions about all of this. The agent reads the GOAL.md, understands what the chunk is trying to accomplish, and makes informed choices about staging, commit consolidation, and conflict resolution as a unified operation.

Resolving conflicts before the reviewer sees the code keeps reviews focused on the integrated reality and removes the failure mode where divergence is only discovered at final merge time, halting automation and requiring manual operator intervention.

## Success Criteria

- A new `WorkUnitPhase.REBASE` value exists in the phase enum
- The phase progression map in `scheduler.py:907-913` includes `IMPLEMENT → REBASE` and `REBASE → REVIEW`
- On entering REBASE, the scheduler always spawns an agent in the worktree
- The agent commits any uncommitted work from the IMPLEMENT phase before merging
- The agent merges main into the worktree branch and resolves any conflicts in light of the chunk's GOAL.md
- The agent runs the test suite to verify the integrated result
- On agent success, the phase advances to REVIEW
- On agent failure (unresolvable conflicts or test failures), the work unit is marked NEEDS_ATTENTION with a descriptive reason including which files conflicted
- The state store migration adds REBASE as a valid phase value
- A REBASE-specific agent prompt template is created that instructs the agent on the commit-merge-resolve-test workflow
- Existing work units in IMPLEMENT phase are unaffected (they'll hit REBASE on their next phase transition)
- All existing scheduler tests pass; new tests cover: clean merge, conflicting merge with agent resolution, uncommitted work handling, and unresolvable merge (NEEDS_ATTENTION)
- The `ve orch status` and dashboard correctly display work units in REBASE phase

## Rejected Ideas

### Rebase instead of merge

We considered using `git rebase main` instead of `git merge main` to maintain linear history. Rejected because: rebase rewrites commit history, which complicates the log trail that the REVIEW and COMPLETE phases rely on. Merge commits are explicit about what was integrated and when. The worktree branches are short-lived anyway — linear history is a concern for main, not for ephemeral orch branches.

### Rebase before every phase

We considered merging trunk before every phase (PLAN, IMPLEMENT, REVIEW, COMPLETE). Rejected because: PLAN and IMPLEMENT phases actively modify files, and a trunk merge mid-work would create unnecessary disruption. The sweet spot is after IMPLEMENT completes and before REVIEW starts — the implementation is done, so we're integrating a stable set of changes.

### Mechanical merge with agent only on conflict

We considered having the scheduler perform `git merge main` mechanically first, then only spawning an agent if conflicts arise (skipping agent invocation on clean merges as a fast path). Rejected because: the IMPLEMENT phase may leave uncommitted files or multiple partial commits that need consolidation before merging. A mechanical merge would lose the context needed to handle these cases. The agent needs to see the full post-IMPLEMENT state to make informed decisions about staging, commit consolidation, and conflict resolution as a unified operation.