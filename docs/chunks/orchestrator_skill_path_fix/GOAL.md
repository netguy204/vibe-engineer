---
status: ACTIVE
ticket: null
parent_chunk: agentskills_migration
code_paths:
- src/orchestrator/agent.py
- tests/test_orchestrator_agent_skills.py
code_references:
  - ref: src/orchestrator/agent.py#PHASE_SKILL_FILES
    implements: "Updated skill name mapping from old .md filenames to bare directory names for .agents/skills/ path structure"
  - ref: src/orchestrator/agent.py#AgentRunner::get_skill_path
    implements: "Canonical skill path construction using .agents/skills/<name>/SKILL.md instead of .claude/commands/<name>.md"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- agentskills_migration
---

# Chunk Goal

## Minor Goal

Fix the orchestrator to use the new agentskills.io skill paths after the
migration. The orchestrator fails at PLAN phase with:

```
[Errno 2] No such file or directory: .claude/commands/chunk-plan.md
```

After `agentskills_migration`, skills moved from `.claude/commands/<name>.md`
to `.agents/skills/<name>/SKILL.md`. The orchestrator still references the old
path format. All chunks injected after the migration are affected.

### What to fix

Search `src/orchestrator/` for any hardcoded references to `.claude/commands/`
or the old `<name>.md` skill filename pattern. Update them to use the new
`.agents/skills/<name>/SKILL.md` path structure.

The `agentskills_migration` chunk set up symlinks (`.claude -> .agents`) for
backwards compatibility, but the orchestrator may be constructing paths directly
rather than going through the symlink. Check whether:

1. The orchestrator constructs skill paths programmatically (needs code fix)
2. The orchestrator reads skill files by path (symlinks should work — investigate
   why they don't)
3. The worktree setup (`_setup_agent_environment_symlinks`) correctly creates
   the `.claude/commands/` symlink in new worktrees

Also check if the orchestrator's worktree manager creates the symlinks before
the agent tries to read skills. A race condition where the agent runs before
symlinks are set up would also cause this error.

## Success Criteria

- Orchestrator PLAN phase succeeds with the new skill path structure
- All orchestrator skill path references updated to `.agents/skills/<name>/SKILL.md`
  or properly resolved through symlinks
- Worktree setup creates necessary symlinks before agent execution
- Existing tests pass
- New test verifying orchestrator finds skills after migration

## Relationship to Parent

Parent chunk `agentskills_migration` moved skills to `.agents/skills/` with
`.claude/commands/` symlinks for backwards compatibility. The migration's
changes to `src/orchestrator/worktree.py` (`_setup_agent_environment_symlinks`
and `_cleanup_agent_environment_symlinks`) were intended to handle this, but
the orchestrator is still failing to find skills at the new paths.
