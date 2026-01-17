<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The Claude Agent SDK documentation reveals that by default, the SDK does not load any filesystem settings. To enable Skills and slash commands from the project's `.claude/commands/` directory, we must:

1. **Configure `setting_sources`**: Add `setting_sources=["project"]` to `ClaudeAgentOptions` so the SDK loads settings from the worktree's `.claude/` directory.

2. **Include "Skill" in `allowed_tools`**: While we use `bypassPermissions` mode which grants all tools, explicitly including "Skill" in `allowed_tools` when permissions are needed ensures the Skill tool is available.

The fix is targeted: modify the `ClaudeAgentOptions` construction in `src/orchestrator/agent.py` to add `setting_sources=["project"]`. The `cwd` is already correctly set to the worktree path, so slash commands defined in `.claude/commands/` will be discovered relative to that path.

**Key insight from SDK docs**: Slash commands from `.claude/commands/` are automatically discovered based on the `cwd` setting, but Skills require explicit `setting_sources` configuration. Since the orchestrator uses the prompts directly (not `/skill-name` invocations), and slash commands are what agents use to invoke chunk phases, the primary fix is ensuring the filesystem settings are loaded.

This approach builds on the existing agent runner architecture established in the `orch_scheduling` chunk.

## Subsystem Considerations

No subsystems are relevant to this chunk. This is a targeted configuration change to the orchestrator's agent runner.

## Sequence

### Step 1: Add setting_sources to ClaudeAgentOptions in run_phase

Modify the `run_phase` method's `ClaudeAgentOptions` construction to include `setting_sources=["project"]`. This enables loading of project-level settings (including Skills and slash commands) from the worktree's `.claude/` directory.

Location: src/orchestrator/agent.py

```python
options = ClaudeAgentOptions(
    cwd=str(worktree_path),
    permission_mode="bypassPermissions",
    max_turns=100,
    setting_sources=["project"],  # Enable project-level skills/commands
)
```

### Step 2: Add setting_sources to ClaudeAgentOptions in run_commit

Apply the same change to the `run_commit` method's options.

Location: src/orchestrator/agent.py

### Step 3: Add setting_sources to ClaudeAgentOptions in resume_for_active_status

Apply the same change to the `resume_for_active_status` method's options.

Location: src/orchestrator/agent.py

### Step 4: Add tests verifying setting_sources configuration

Write tests that verify:
1. The `ClaudeAgentOptions` passed to `query()` includes `setting_sources=["project"]`
2. This is consistent across all methods that create options (`run_phase`, `run_commit`, `resume_for_active_status`)

These tests will mock the `query()` function and capture the options passed to it.

Location: tests/test_orchestrator_agent.py

### Step 5: Update documentation

Add a brief note to the investigation design document about which SDK configuration enables skill access, for future reference.

Location: docs/investigations/parallel_agent_orchestration/OVERVIEW.md (Architectural Decisions section)

## Dependencies

- **orch_scheduling chunk**: This chunk modifies `src/orchestrator/agent.py` which was created by the scheduling chunk.
- **Claude Agent SDK**: The `setting_sources` parameter must be supported by the installed version of `claude-agent-sdk`. Per the SDK documentation, this is a core configuration option.

## Risks and Open Questions

1. **SDK version compatibility**: The `setting_sources` parameter is documented in current SDK documentation. If an older SDK version is in use, this parameter may not be supported. Mitigation: Check the SDK version constraints in `pyproject.toml` if the parameter causes errors.

2. **User-level skills**: The goal explicitly excludes user-level skills (`~/.claude/commands/`). We're only including `"project"` in `setting_sources`, not `"user"`. This is intentional - background agents should only use project-defined skills.

3. **Skill vs Command terminology**: The SDK distinguishes between:
   - **Skills** (`.claude/skills/SKILL.md`): Claude autonomously invokes based on context
   - **Slash Commands** (`.claude/commands/foo.md`): Explicitly invoked via `/foo`

   The worktree has commands, not skills. The `setting_sources` configuration enables both, so this should work. However, if agents need to explicitly invoke skills (not commands), they'd need the Skill tool. This is out of scope since the orchestrator uses prompt injection of skill content, not agent-initiated skill invocation.

4. **bypassPermissions mode interaction**: We use `permission_mode="bypassPermissions"` which grants all tools. The `setting_sources` parameter should be orthogonal to this - it controls where settings are loaded from, not permissions. If there's an interaction, we may need to also add `allowed_tools=["Skill"]` explicitly.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->