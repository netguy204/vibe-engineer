---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/agent.py
  - tests/test_orchestrator_agent.py
  - docs/investigations/parallel_agent_orchestration/OVERVIEW.md
code_references:
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "setting_sources=['project'] configuration for phase execution enabling project-level skills"
  - ref: src/orchestrator/agent.py#AgentRunner::run_commit
    implements: "setting_sources=['project'] configuration for commit phase enabling project-level skills"
  - ref: src/orchestrator/agent.py#AgentRunner::resume_for_active_status
    implements: "setting_sources=['project'] configuration for session resume enabling project-level skills"
  - ref: tests/test_orchestrator_agent.py#TestSettingSourcesConfiguration
    implements: "Test coverage verifying setting_sources configuration is passed to ClaudeAgentOptions"
  - ref: docs/investigations/parallel_agent_orchestration/OVERVIEW.md
    implements: "Documentation of SDK configuration for project-level skills under Architectural Decisions"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- ordering_field_clarity
---

# Chunk Goal

## Minor Goal

Configure background agents spawned by the orchestrator to have access to the same skills (slash commands) that interactive Claude Code users have.

Currently, background agents run in isolated worktrees that contain the project's `.claude/` configuration directory with skills defined in `.claude/commands/`. However, the transcript audit revealed agents receiving errors like `Unknown skill: chunk-resolve-references` when trying to use skills that should be available.

The Claude Agent SDK provides configuration options to make project-level Claude config available to spawned agents. This chunk will:
- Ensure the worktree's `.claude/commands/` directory is recognized by background agents
- Configure the agent runner to use project-level skills
- Give background agents feature parity with interactive users for skill access

## Success Criteria

1. **Background agents can invoke project-level skills**
   - Skills defined in `.claude/commands/` are available to background agents
   - `Skill` tool calls succeed instead of returning "Unknown skill" errors
   - Skills like `/chunk-commit`, `/chunk-complete`, etc. work in background agents

2. **Agent runner configuration is updated**
   - `src/orchestrator/agent.py` passes appropriate config to enable skills
   - Worktree path is used as the project directory for skill resolution
   - Claude Agent SDK `cwd` or equivalent config is set correctly

3. **Skills resolve from the worktree context**
   - Each agent session uses skills from its own worktree (not the main repo)
   - Different chunks running in parallel use their respective worktree skills
   - Skill content reflects the worktree's version of `.claude/commands/`

4. **Documentation of SDK configuration**
   - Document which Claude Agent SDK options enable skill access
   - Note any limitations or differences from interactive mode
   - Update orchestrator documentation with skill availability info

## Out of Scope

- Creating new skills specifically for background agents
- Modifying existing skill content
- MCP server access (separate concern)
- User-level skills from `~/.claude/commands/` (project-level only)