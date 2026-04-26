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

Worktree finalization in the orchestrator reaps any child processes still
rooted in the worktree path, so torn-down worktrees do not leave behind
long-lived zombies that hog memory or hold external tokens.

### The hazard being closed

When the orchestrator tears down a worktree (merge, force-remove, branch
delete), child processes spawned during phase execution (PLAN/IMPLEMENT/REVIEW)
— particularly claude-agent-sdk bundled Claude Code subprocesses — can
continue running indefinitely after the worktree directory is removed. The
motivating incident: 7 zombie processes at ~100-220MB RSS each, running 5+
hours after the chunk was marked DONE and its worktree removed.

The downstream harm is shaped by what the zombies hold. In the motivating
incident one held a Slack App-Level Token, causing the operator's fresh
Slack adapter to churn ("session established / session abandoned" every
~125ms) and silently drop all inbound DMs. Only
`pkill -f "\.ve/chunks/.*worktree"` resolved it. The same shape applies to
any external resource (file locks, network connections, tokens) a phase
agent might hold.

### Reproducer

Inject any chunk whose phases exercise claude-agent-sdk, let the
orchestrator complete it, then:

```bash
ps aux | grep '.ve/chunks/.*/worktree' | grep -v grep
```

If processes remain, the worktree teardown failed to reap them.

### Implementation shape

`WorktreeManager._remove_worktree_from_repo` calls
`_reap_worktree_processes(worktree_path)` before invoking
`git worktree remove` (`src/orchestrator/worktree.py`).
`_reap_worktree_processes`:

1. **Scans for child processes** — uses `psutil.process_iter` to find
   processes whose `cwd` or any `cmdline` arg is inside the worktree path
   being removed. The orchestrator's own PID is excluded.
2. **SIGTERM → grace period → SIGKILL** — sends SIGTERM to all candidates,
   waits 5 seconds, then SIGKILL for any survivors.
3. **Logs** — emits WARNING-level log entries naming the reaped PIDs and
   any that required SIGKILL.

Running phase agents in their own process group (`os.setpgrp()`) inside the
scheduler is a possible future hardening, but is not part of this chunk —
the path-based scan covers the observed cases.

### Cross-project context

Reported by the world-model project. The impact was amplified because zombie
processes held external tokens (Slack), but the underlying hazard affects
any project using the orchestrator — zombies consume memory and may hold
file locks, network connections, or other resources.

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