---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- src/orchestrator/scheduler.py
- tests/test_orchestrator_worktree.py
code_references:
- ref: src/orchestrator/worktree.py#WorktreeManager::_reap_worktree_processes
  implements: "Core process-reaping logic: scan for processes in worktree path, SIGTERM → wait 5s → SIGKILL survivors"
- ref: src/orchestrator/worktree.py#WorktreeManager::_remove_worktree_from_repo
  implements: "Integration point: calls _reap_worktree_processes before git worktree removal"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- wiki_identity_routing
---


# Chunk Goal

## Minor Goal

Reap child processes spawned inside orchestrator worktrees during finalization,
preventing long-lived zombie processes that hog memory and break external
token-based services.

### The bug

When the orchestrator tears down a worktree (merge, force-remove, branch
delete), child processes spawned during phase execution (PLAN/IMPLEMENT/REVIEW)
— particularly claude-agent-sdk bundled Claude Code subprocesses — continue
running indefinitely. Observed: 7 zombie processes with ~100-220MB RSS each,
running 5+ hours after the chunk was marked DONE and its worktree removed.

Real-world harm: one of those zombies held a Slack App-Level Token, causing
the operator's fresh Slack adapter to churn ("session established / session
abandoned" every ~125ms) and silently drop all inbound DMs. Only
`pkill -f "\.ve/chunks/.*worktree"` resolved it.

### Reproducer

Inject any chunk whose phases exercise claude-agent-sdk, let the orchestrator
complete it, then:

```bash
ps aux | grep '.ve/chunks/.*/worktree' | grep -v grep
```

If processes remain, the bug is present.

### Implementation approach

In `WorktreeManager.remove_worktree()` (`src/orchestrator/worktree.py`),
before removing the worktree directory:

1. **Scan for child processes** — use `psutil` (or `ps aux` parsing as
   fallback) to find processes whose cwd or exe path is inside the worktree
   path being removed.
2. **SIGTERM → grace period → SIGKILL** — send SIGTERM to found processes,
   wait briefly (e.g., 5 seconds), then SIGKILL any remaining.
3. **Log** — log at WARNING level which PIDs were reaped and why.

Additionally, consider running phase agents in their own process group
(`os.setpgrp()`) during `_run_phase()` in the scheduler, so the entire
group can be terminated cleanly at teardown. This is a more robust long-term
solution but requires changes to how the scheduler spawns agents.

### Cross-project context

Reported by the world-model project. The impact was amplified because zombie
processes held external tokens (Slack), but the underlying bug affects any
project using the orchestrator — zombies consume memory and may hold file
locks, network connections, or other resources.

## Success Criteria

- `remove_worktree` kills child processes rooted in the worktree path before
  removing the directory
- SIGTERM is sent first with a grace period before SIGKILL
- Reaped processes are logged at WARNING level
- Test covers the reap behavior (mock process discovery + kill)
- Existing orchestrator tests pass

## Rejected Ideas

<!-- DELETE THIS SECTION when the goal is confirmed if there were no rejected
ideas.

This is where the back-and-forth between the agent and the operator is recorded
so that future agents understand why we didn't do something.

If there were rejected ideas in the development of this GOAL with the operator,
list them here with the reason they were rejected.

Example:

### Store the queue in redis

We could store the queue in redis instead of a file. This would allow us to scale the queue to multiple nodes.

Rejected because: The queue has no meaning outside the current session.

---

-->