<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Implement defense-in-depth sandbox enforcement using three complementary layers:

1. **Hook-based Command Filtering (Primary)**: Register a Claude Code PreToolUse
   hook when launching agents that intercepts Bash tool calls and blocks commands
   that would escape the worktree. This is similar to the existing
   `create_question_intercept_hook()` pattern.

2. **Git Environment Restriction**: Set `GIT_DIR` and `GIT_WORK_TREE` environment
   variables when launching agents to restrict git operations to the worktree.

3. **Prompt Hardening**: Add explicit sandbox rules to the CWD reminder already
   prepended to phase prompts.

The key constraint is **dynamic path detection**: all paths must be derived at
runtime from the orchestrator's known state (host repo path from startup, worktree
path per-agent), not hard-coded.

This follows the existing hook pattern in `agent.py` (see
`create_question_intercept_hook`) and leverages the Claude Agent SDK's
`PreToolUseHookInput`, `SyncHookJSONOutput`, and `HookMatcher` types.

Test strategy per TESTING_PHILOSOPHY.md:
- Unit tests for the hook blocking logic with semantic assertions about which
  commands are blocked/allowed
- Test dynamic path detection (no hard-coded paths)
- Test git environment setup
- All existing orchestrator tests must continue to pass

## Subsystem Considerations

No relevant subsystems identified. This work is specific to orchestrator agent
sandbox enforcement and doesn't touch template_system or workflow_artifacts.

## Sequence

### Step 1: Create sandbox hook utility function

Add a new function `create_sandbox_enforcement_hook()` to `src/orchestrator/agent.py`
that creates a PreToolUse hook for Bash commands.

The function signature:
```python
def create_sandbox_enforcement_hook(
    host_repo_path: Path,
    worktree_path: Path,
) -> dict[str, list[HookMatcher]]:
```

The hook logic should:
- Match on tool_name "Bash"
- Extract the command from `tool_input.get("command", "")`
- Check for violations:
  - `cd {host_repo_path}` (with optional quotes)
  - Any command containing `{host_repo_path}` as a path in git operations
  - `cd /absolute/path` where path is outside `{worktree_path}`
- Return `SyncHookJSONOutput(decision="block", reason="...")` for violations
- Return `SyncHookJSONOutput(decision="allow")` for safe commands

Location: `src/orchestrator/agent.py`

### Step 2: Add path violation detection helper

Create helper function `_is_sandbox_violation()` to centralize the path checking logic:

```python
def _is_sandbox_violation(
    command: str,
    host_repo_path: Path,
    worktree_path: Path,
) -> tuple[bool, str | None]:
    """Check if a command violates sandbox rules.

    Returns:
        Tuple of (is_violation, reason) where reason explains the violation.
    """
```

This function should detect:
- Direct `cd` to host repo (with/without quotes)
- Git commands with `-C` flag pointing to host repo
- Git commands with explicit path arguments to host repo
- Any `cd` to absolute paths outside the worktree

Location: `src/orchestrator/agent.py`

### Step 3: Store host_repo_path in AgentRunner

Modify `AgentRunner.__init__()` to store the host repo path as an instance
attribute. This is the path where the orchestrator was started (passed to
AgentRunner at construction time, derived from `project_dir`).

```python
def __init__(self, project_dir: Path):
    self.project_dir = project_dir.resolve()
    self.host_repo_path = project_dir.resolve()  # Same as project_dir
```

Location: `src/orchestrator/agent.py`

### Step 4: Integrate sandbox hook into run_phase

Modify `run_phase()` to always configure the sandbox enforcement hook:

```python
# Build sandbox enforcement hook
sandbox_hooks = create_sandbox_enforcement_hook(
    host_repo_path=self.host_repo_path,
    worktree_path=worktree_path,
)

# Merge with question hook if present
if question_callback:
    question_hooks = create_question_intercept_hook(on_question)
    hooks = _merge_hooks(sandbox_hooks, question_hooks)
else:
    hooks = sandbox_hooks

options.hooks = hooks
```

Also need a helper to merge multiple hook configurations:
```python
def _merge_hooks(
    *hook_configs: dict[str, list[HookMatcher]],
) -> dict[str, list[HookMatcher]]:
    """Merge multiple hook configurations."""
```

Location: `src/orchestrator/agent.py`

### Step 5: Add git environment variables

Modify `run_phase()` to pass environment variables that restrict git operations.
The Claude Agent SDK's `ClaudeAgentOptions` should support environment configuration.

If `ClaudeAgentOptions` supports an `env` parameter:
```python
env = os.environ.copy()
env["GIT_DIR"] = str(worktree_path / ".git")
env["GIT_WORK_TREE"] = str(worktree_path)

options = ClaudeAgentOptions(
    cwd=str(worktree_path),
    env=env,  # If supported
    ...
)
```

If not supported, document this limitation and rely on hook enforcement as the
primary defense.

Location: `src/orchestrator/agent.py`

### Step 6: Enhance prompt with sandbox rules

Modify the CWD reminder in `run_phase()` to include explicit sandbox rules:

```python
cwd_reminder = (
    f"**Working Directory:** `{worktree_path}`\n"
    f"Use relative paths (e.g., `docs/chunks/...`) or paths relative to this directory.\n"
    f"Do NOT guess absolute paths from memory - they will be wrong.\n\n"
    f"## SANDBOX RULES (CRITICAL)\n\n"
    f"You are operating in an isolated git worktree. You MUST:\n"
    f"- NEVER use `cd` with absolute paths outside this directory\n"
    f"- NEVER run git commands targeting the host repository\n"
    f"- ALWAYS use relative paths from the current worktree\n"
    f"- ONLY commit to the current branch in this worktree\n\n"
    f"Violations will be blocked and logged.\n\n"
)
```

Location: `src/orchestrator/agent.py`

### Step 7: Apply sandbox hook to other agent methods

Ensure sandbox enforcement is also applied to:
- `run_commit()` - though deprecated, should still be protected
- `resume_for_active_status()` - uses agent to edit files

Each of these methods should get the sandbox hook configured.

Location: `src/orchestrator/agent.py`

### Step 8: Write unit tests for sandbox hook

Create tests in `tests/test_orchestrator_agent.py`:

```python
class TestSandboxEnforcementHook:
    """Tests for sandbox enforcement hook."""

    def test_blocks_cd_to_host_repo(self):
        """Hook blocks cd to host repository path."""

    def test_blocks_cd_to_host_repo_with_quotes(self):
        """Hook blocks cd with quoted paths."""

    def test_blocks_git_command_with_host_path(self):
        """Hook blocks git -C /host/path commit."""

    def test_allows_commands_within_worktree(self):
        """Hook allows normal commands in worktree."""

    def test_allows_relative_cd(self):
        """Hook allows cd with relative paths."""

    def test_blocks_absolute_cd_outside_worktree(self):
        """Hook blocks cd to absolute path outside worktree."""

    def test_allows_cd_within_worktree(self):
        """Hook allows cd to paths within worktree."""

    def test_dynamic_path_detection(self):
        """Hook uses provided paths, not hardcoded values."""
```

Location: `tests/test_orchestrator_agent.py`

### Step 9: Test hook integration with run_phase

Add integration tests verifying the hook is properly configured:

```python
class TestSandboxHookIntegration:
    """Tests for sandbox hook integration in run_phase."""

    @pytest.mark.asyncio
    async def test_run_phase_configures_sandbox_hook(self):
        """run_phase includes sandbox enforcement hook."""

    @pytest.mark.asyncio
    async def test_sandbox_hook_combined_with_question_hook(self):
        """Both sandbox and question hooks work together."""
```

Location: `tests/test_orchestrator_agent.py`

### Step 10: Test environment variable configuration

Add tests for git environment restriction (if supported by SDK):

```python
class TestGitEnvironmentRestriction:
    """Tests for git environment variable configuration."""

    @pytest.mark.asyncio
    async def test_git_dir_environment_set(self):
        """GIT_DIR environment points to worktree."""

    @pytest.mark.asyncio
    async def test_git_work_tree_environment_set(self):
        """GIT_WORK_TREE environment points to worktree."""
```

Location: `tests/test_orchestrator_agent.py`

### Step 11: Run full test suite

Ensure all existing tests pass:

```bash
uv run pytest tests/ -v
```

Specifically verify:
- All `test_orchestrator_*.py` tests pass
- No regressions in question forwarding behavior
- Hook configuration doesn't interfere with normal operations

Location: Command line

### Step 12: Update GOAL.md code_paths

Update the chunk's GOAL.md with the files touched:

```yaml
code_paths:
  - src/orchestrator/agent.py
  - tests/test_orchestrator_agent.py
```

Location: `docs/chunks/orch_sandbox_enforcement/GOAL.md`

## Dependencies

- Existing `create_question_intercept_hook()` pattern in `src/orchestrator/agent.py`
- Claude Agent SDK types: `PreToolUseHookInput`, `SyncHookJSONOutput`, `HookMatcher`
- No external dependencies to add

## Risks and Open Questions

1. **SDK environment support**: The Claude Agent SDK's `ClaudeAgentOptions` may
   not support an `env` parameter for setting environment variables. If not, the
   git environment restriction layer won't be implementable, and we'll need to
   rely more heavily on the hook-based enforcement.

2. **Path matching edge cases**: Complex command strings with pipes, subshells,
   or variable expansion may evade simple string matching. The hook provides a
   primary defense, but determined agents could potentially construct evasion
   commands. The prompt hardening layer provides additional guidance.

3. **Hook execution order**: When multiple hooks are configured (sandbox +
   question), the order of execution and how they interact needs verification.
   Both should be able to independently block.

4. **Performance**: Adding a hook that inspects every Bash command adds overhead.
   This should be negligible but worth monitoring if agents execute many commands.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
