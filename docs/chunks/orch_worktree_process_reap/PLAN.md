

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

We add a process-reaping step to `WorktreeManager._remove_worktree_from_repo()` so that any
child processes whose current working directory (cwd) or executable path is inside the worktree
are terminated before the worktree directory is removed.

**Library choice — `psutil` over `ps aux` parsing**:
`psutil` is the de-facto Python standard for process inspection. It provides reliable,
cross-platform process enumeration with per-process cwd and cmdline access, with no shell-injection
risk. We add it as an explicit dependency in `pyproject.toml`. A `ps aux` / shell-based fallback
is **not** needed; `psutil` is available on all platforms we target.

**Signal sequence**:
1. Send `SIGTERM` to each found process.
2. Wait up to 5 seconds for processes to exit.
3. Send `SIGKILL` to any that remain.
4. Log at `WARNING` level for each PID reaped (including which signal finished them).

**Placement**: The reap call goes into `_remove_worktree_from_repo()`, *before* the
`git worktree remove` call. This ensures processes are gone before git tries to remove the
directory (avoiding "device or resource busy" errors on some OS).

**Process group / `setpgrp` approach**: The GOAL.md mentions optionally setting a new process
group for phase agents so the entire group can be killed at teardown. After reviewing
`AgentRunner.run_phase()`, the actual subprocess is spawned inside the `claude-agent-sdk`
library, making `setpgrp` integration non-trivial without SDK changes. We defer this to a
future chunk. The `psutil`-based cwd scan is sufficient to fix the immediate bug and aligns
with the GOAL's "Approach" section priority ordering.

Relates to: `docs/subsystems/orchestrator` (this chunk IMPLEMENTS worktree teardown
correctness within the orchestrator subsystem).

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a fix within
  `WorktreeManager`, which is a core component of the orchestrator subsystem. No deviations
  from subsystem patterns were discovered; we are adding behaviour to an existing method.

## Sequence

### Step 1: Add `psutil` to dependencies

In `pyproject.toml`, add `"psutil>=5.9"` to the `dependencies` list (alphabetically after
`pynacl`, before `pyyaml`).

Run `uv sync` to verify the package resolves cleanly.

### Step 2: Implement `_reap_worktree_processes` helper on `WorktreeManager`

Add a new private method to `WorktreeManager` in `src/orchestrator/worktree.py`:

```python
# Chunk: docs/chunks/orch_worktree_process_reap - Kill stray child processes before worktree removal
def _reap_worktree_processes(self, worktree_path: Path) -> None:
    """Terminate processes whose cwd or exe is inside worktree_path.

    Sends SIGTERM first, waits up to 5 seconds, then SIGKILL for any
    remaining processes.  All reaped PIDs are logged at WARNING level.

    Args:
        worktree_path: Absolute path to the worktree being removed.
    """
```

Implementation notes:
- Import `signal`, `time`, and `psutil` at the top of the module.
- Iterate `psutil.process_iter(['pid', 'cwd', 'cmdline'])`, catching
  `psutil.NoSuchProcess`, `psutil.AccessDenied`, and `psutil.ZombieProcess`
  per-process (they are transient races; skip silently).
- A process is a candidate if its `cwd` starts with `str(worktree_path)` **or**
  any element of its `cmdline` contains `str(worktree_path)`.
- Skip `psutil.Process(os.getpid())` (the orchestrator itself) to avoid
  self-termination in edge cases.
- Send `SIGTERM` to all candidates, then `time.sleep(5)`, then `SIGKILL` to
  survivors. Wrap each kill in a `try/except psutil.NoSuchProcess` (process may
  have exited naturally during the grace period).
- Log at `WARNING`: `"Reaping %d process(es) in worktree %s: PIDs %s"` before
  SIGTERM. Log at `WARNING` per PID that required SIGKILL.
- If no processes are found, skip logging entirely (no noise in the happy path).

### Step 3: Call `_reap_worktree_processes` from `_remove_worktree_from_repo`

At the top of `_remove_worktree_from_repo`, before the `_unlock_worktree` call,
add:

```python
# Chunk: docs/chunks/orch_worktree_process_reap - Reap stray processes before removal
self._reap_worktree_processes(worktree_path)
```

This ensures cleanup happens for both single-repo and task-context removal paths,
since both ultimately call `_remove_worktree_from_repo`.

Add a backreference comment at the method level:
```python
# Chunk: docs/chunks/orch_worktree_process_reap - Reap stray processes before removal
```

### Step 4: Write tests in `tests/test_orchestrator_worktree.py`

Add a new test class `TestReapWorktreeProcesses` to
`tests/test_orchestrator_worktree.py` (the pre-existing "split file" entry point
is fine — the comment there says backward compatibility is the goal; adding a new
class here is appropriate rather than adding yet another split file).

Tests to write (all use `unittest.mock.patch` to avoid real process operations):

**Test 1 — processes in worktree are sent SIGTERM then SIGKILL if they survive**

Mock `psutil.process_iter` to return a fake process whose `cwd()` is inside the
worktree path. Assert `SIGTERM` is sent. Mock the process as still alive after the
grace period. Assert `SIGKILL` is sent and a WARNING is logged.

```python
def test_reap_sends_sigterm_then_sigkill_to_survivors(self, git_repo):
    ...
```

**Test 2 — processes that exit after SIGTERM are not SIGKILL'd**

Same setup, but mock the process as exiting (raising `psutil.NoSuchProcess`)
when SIGKILL would be sent. Assert no SIGKILL call was attempted against an
already-dead process.

```python
def test_reap_skips_sigkill_for_exited_processes(self, git_repo):
    ...
```

**Test 3 — processes outside the worktree path are not reaped**

Mock `psutil.process_iter` to return a process whose `cwd()` is in a completely
different directory. Assert neither SIGTERM nor SIGKILL is sent.

```python
def test_reap_ignores_processes_outside_worktree(self, git_repo):
    ...
```

**Test 4 — no processes → no log noise**

Mock `psutil.process_iter` to return an empty list. Assert no WARNING is logged.

```python
def test_reap_no_log_when_no_processes_found(self, git_repo, caplog):
    ...
```

**Test 5 — `remove_worktree` calls the reaper before git remove (integration)**

In a real git repo fixture, create a worktree and then call `remove_worktree`.
Patch `_reap_worktree_processes` and assert it was called with the correct
`worktree_path` before the directory is removed.

```python
def test_remove_worktree_calls_reaper_before_removal(self, git_repo):
    ...
```

Test execution:
```bash
uv run pytest tests/test_orchestrator_worktree.py -v -k "TestReapWorktreeProcesses"
```

All existing tests must continue to pass:
```bash
uv run pytest tests/
```

### Step 5: Verify the `psutil` import doesn't break the happy path

Since `psutil` process iteration may fail in restricted environments (containers
with limited `/proc` access), wrap the entire `psutil.process_iter(...)` call in a
broad `try/except Exception` with a `logger.debug("psutil scan skipped: %s", e)`
fallback. This ensures the worktree is always removed, even if process inspection
fails.

Add this guard in Step 2 while writing the helper.

## Dependencies

- `psutil>=5.9` must be added to `pyproject.toml` and resolved before
  implementing Step 2.

## Risks and Open Questions

- **`psutil.AccessDenied` on cwd access**: Some OS configurations or containers
  may deny reading the cwd of certain processes. Handled by per-process
  `try/except` in the scan loop.

- **False positives**: A process whose cmdline string happens to contain the
  worktree path string (e.g., a `grep` of the path) could be killed. This is
  acceptable — such processes are transient and the worktree is being torn down
  anyway. The cwd check is the primary discriminator; cmdline is secondary.

- **Grace period duration**: 5 seconds is a judgement call. Claude Code
  subprocesses typically exit quickly on SIGTERM. If SIGKILL is triggered
  frequently in practice, the grace period should be increased in a follow-up chunk.

- **Process groups / `setpgrp`**: More robust long-term solution but deferred
  because it requires changes inside `claude-agent-sdk` or wrapping agent
  subprocess spawning. Documented in the Rejected Ideas section is not needed since
  the GOAL.md already describes this as a secondary "consider" — we simply note the
  deferral here.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
