---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/chunk-create.md.jinja2
- src/templates/chunk/GOAL.md.jinja2
- .claude/commands/chunk-create.md
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Step 10 - IMPORTANT commit guidance instructing agents to add entire chunk directory"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "COMMIT BOTH FILES section added to FUTURE CHUNK APPROVAL REQUIREMENT"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- disclosure_trunk_templates
---

# Chunk Goal

## Minor Goal

Add explicit prompting guidance for agents to commit both GOAL.md and PLAN.md when committing a new chunk before injection.

**The problem:** When `ve chunk create` runs, it creates both GOAL.md and PLAN.md from templates. The agent then refines GOAL.md. When the operator says "commit and inject":
1. Agent runs `git add <chunk>/GOAL.md` (only the file it modified)
2. PLAN.md remains as an untracked file on main
3. Agent injects the chunk
4. Orchestrator runs PLAN phase, creating/modifying PLAN.md in its worktree
5. Merge fails: "untracked working tree files would be overwritten by merge"

**Root cause:** The agent only adds files it modified to the commit, but `ve chunk create` creates both GOAL.md and PLAN.md. The untracked PLAN.md on main causes the merge conflict.

**Solution:** Update prompting to instruct agents: when committing a newly created chunk, add both GOAL.md and PLAN.md to the commit (the entire chunk directory), even if only GOAL.md was modified.

## Success Criteria

- Update chunk-create skill to explicitly instruct: "When committing a new chunk, add the entire chunk directory (both GOAL.md and PLAN.md)"
- Alternatively: add guidance to the FUTURE CHUNK APPROVAL REQUIREMENT section in GOAL.md template
- After fix: agents commit both files, preventing untracked file conflicts on merge
- Existing tests pass