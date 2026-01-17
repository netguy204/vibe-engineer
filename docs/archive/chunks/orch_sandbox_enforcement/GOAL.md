---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/agent.py
- tests/test_orchestrator_agent.py
code_references:
  - ref: src/orchestrator/agent.py#_is_sandbox_violation
    implements: "Sandbox violation detection logic for cd and git commands"
  - ref: src/orchestrator/agent.py#_merge_hooks
    implements: "Hook configuration merging for multiple PreToolUse handlers"
  - ref: src/orchestrator/agent.py#create_sandbox_enforcement_hook
    implements: "PreToolUse hook that blocks commands escaping worktree sandbox"
  - ref: src/orchestrator/agent.py#AgentRunner::__init__
    implements: "Store host_repo_path for sandbox enforcement"
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Sandbox hook, git environment, and prompt hardening integration"
  - ref: src/orchestrator/agent.py#AgentRunner::run_commit
    implements: "Sandbox hook and git environment for commit operations"
  - ref: src/orchestrator/agent.py#AgentRunner::resume_for_active_status
    implements: "Sandbox hook and git environment for resume operations"
  - ref: tests/test_orchestrator_agent.py#TestSandboxViolationDetection
    implements: "Unit tests for _is_sandbox_violation detection logic"
  - ref: tests/test_orchestrator_agent.py#TestMergeHooks
    implements: "Unit tests for hook configuration merging"
  - ref: tests/test_orchestrator_agent.py#TestSandboxEnforcementHook
    implements: "Unit tests for sandbox enforcement hook creation and behavior"
  - ref: tests/test_orchestrator_agent.py#TestAgentRunnerSandboxIntegration
    implements: "Integration tests for sandbox enforcement in AgentRunner methods"
narrative: null
investigation: null
subsystems: []
created_after:
- orch_attention_queue
- orch_conflict_oracle
- orch_agent_skills
- orch_question_forward
---

# Chunk Goal

## Minor Goal

Prevent orchestrator agents from escaping their worktree sandbox and modifying
the host repository directly. This addresses a critical bug discovered during
investigation of the `artifact_copy_backref` work unit, where an agent ran
`cd /path/to/host && git commit` and committed unrelated changes directly to
main instead of to the worktree branch. The implementation was lost because
the worktree had no commits to merge.

The fix implements defense-in-depth with three layers:

### 1. Hook-based Command Filtering (Primary Enforcement)

Register a Claude Code hook when launching agents that intercepts Bash tool
calls and blocks commands that would escape the worktree:

- Block commands containing `cd <host_repo_path>` (absolute path to host)
- Block commands containing the host repo path in git operations
- Block any `cd` to an absolute path outside the worktree

**Critical**: Paths must be dynamically derived at runtime:
- `host_repo_path`: The directory where `ve orch start` was launched (available
  from orchestrator state or `os.getcwd()` at startup)
- `worktree_path`: The actual worktree path for the current chunk (e.g.,
  `.ve/chunks/<chunk>/worktree`)

Do NOT hard-code paths like `/Users/btaylor/Projects/vibe-engineer`.

### 2. Git Environment Restriction

When launching agents, set environment variables that restrict git operations
to the worktree only:

```python
env = os.environ.copy()
env["GIT_DIR"] = str(worktree_path / ".git")
env["GIT_WORK_TREE"] = str(worktree_path)
```

This causes git commands to operate on the worktree even if the agent somehow
changes directory to the host repo.

### 3. Prompt Hardening (Guidance Layer)

Add explicit sandbox rules to the CWD reminder already prepended to phase
prompts (in `src/orchestrator/agent.py`):

```markdown
## SANDBOX RULES (CRITICAL)

You are operating in an isolated git worktree. You MUST:
- NEVER use `cd` with absolute paths outside this directory
- NEVER run git commands targeting the host repository
- ALWAYS use relative paths from the current worktree
- ONLY commit to the current branch in this worktree

Violations will be blocked and logged.
```

## Success Criteria

- **Hook registration**: `AgentRunner` registers a sandbox enforcement hook
  when creating `ClaudeAgentOptions` that intercepts Bash commands
- **Dynamic path detection**: Hook uses `self.host_repo_path` (captured at
  orchestrator startup) and `worktree_path` (passed per-agent) - no hard-coded
  paths in the codebase
- **Blocking behavior**: Hook returns `SyncHookJSONOutput(decision="block", ...)`
  for commands matching:
  - `cd {host_repo_path}` or `cd '{host_repo_path}'` or `cd "{host_repo_path}"`
  - Any git command containing `{host_repo_path}`
  - `cd /absolute/path` where path is outside `{worktree_path}`
- **Git environment**: Agent subprocess environment includes `GIT_DIR` and
  `GIT_WORK_TREE` pointing to the worktree
- **Prompt hardening**: Phase prompts include sandbox rules warning agents
  about isolation requirements
- **Test coverage**:
  - Unit test verifying hook blocks `cd /host/repo/path`
  - Unit test verifying hook blocks `git -C /host/repo/path commit`
  - Unit test verifying hook allows normal commands within worktree
  - Unit test verifying `GIT_DIR` environment is set correctly
- **No regressions**: All existing orchestrator tests pass

