---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/AGENTS.md.jinja2
- src/templates/commands/
- src/project.py
- src/template_system.py
- src/task_init.py
- src/orchestrator/worktree.py
- tests/test_project.py
- tests/test_init.py
code_references:
- ref: src/template_system.py#render_to_directory
  implements: "skill_layout parameter for agentskills.io <name>/SKILL.md directory structure"
- ref: src/project.py#Project::_init_skills
  implements: "Renders skills to .agents/skills/ and creates .claude/commands/ backwards-compat symlinks"
- ref: src/project.py#Project::_init_agents_md
  implements: "AGENTS.md as canonical instructions file with CLAUDE.md symlink and migration from pre-existing CLAUDE.md"
- ref: src/task_init.py#TaskInit::_render_agents_md
  implements: "Task-context AGENTS.md rendering with CLAUDE.md symlink"
- ref: src/task_init.py#TaskInit::_render_skills
  implements: "Task-context skill rendering to .agents/skills/ with .claude/commands/ symlinks"
- ref: src/orchestrator/worktree.py#WorktreeManager::_setup_agent_environment_symlinks
  implements: "Worktree symlinks for AGENTS.md and .agents/ alongside existing CLAUDE.md and .claude/"
- ref: src/orchestrator/worktree.py#WorktreeManager::_cleanup_agent_environment_symlinks
  implements: "Cleanup of AGENTS.md and .agents symlinks in worktree teardown"
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: "Renamed canonical template from CLAUDE.md.jinja2"
- ref: src/templates/task/AGENTS.md.jinja2
  implements: "Renamed task template from CLAUDE.md.jinja2"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: implements
- subsystem_id: cross_repo_operations
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- skill_chunk_execute_review_loop
---

# Chunk Goal

## Minor Goal

Migrate VE's Claude-specific command structure to the open skill standard
at https://agentskills.io/specification. This is a cross-project request from
the uniharness steward to enable skill interoperability between VE and
uniharness sessions.

### What needs to change

1. **AGENTS.md as canonical** — Move VE-managed content from `CLAUDE.md` to
   `AGENTS.md`. The `AGENTS.md` file becomes the canonical agent instructions
   file. For backwards compatibility with Claude Code, `ve init` should create
   a symlink: `CLAUDE.md -> AGENTS.md`.

2. **`.agents/` directory** — Move skill storage from `.claude/commands/` to
   `.agents/skills/` following the agentskills.io directory spec. For backwards
   compatibility, `ve init` should create a symlink: `.claude -> .agents`
   (or `.claude/commands -> .agents/skills`).

3. **SKILL.md format** — Skills should follow the agentskills.io SKILL.md
   format for discovery. Study the specification at
   https://agentskills.io/specification and the uniharness implementation at
   `src/uniharness/skills.py` (in the uniharness repo) to understand the
   format. Each skill directory should contain a `SKILL.md` with frontmatter
   for metadata (name, description, triggers) and body for instructions.

4. **Template rendering** — Update `ve init` to render templates into the new
   directory structure. The Jinja2 templates in `src/templates/commands/` should
   render to `.agents/skills/<name>/SKILL.md` instead of
   `.claude/commands/<name>.md`.

### Key constraints

- **Backwards compatibility** — Claude Code must continue to work. It reads
  `CLAUDE.md` and `.claude/commands/`. Symlinks preserve this.
- **No functional changes** — Skills should behave identically. This is a
  structural migration, not a behavior change.
- **Symlink strategy** — Symlinks are the compatibility bridge. `ve init`
  creates them. If a user has existing `.claude/` content, handle gracefully.

### Cross-project context

This request came from the uniharness steward. Uniharness already searches
`.agents/skills/` for `SKILL.md` files. Making VE use the same standard means
skills authored in the VE workflow work in uniharness sessions (Gemini, Codex,
etc.) without modification.

## Success Criteria

- `ve init` creates `.agents/skills/` directory with SKILL.md files
- `ve init` creates `AGENTS.md` as the canonical instructions file
- Symlinks: `CLAUDE.md -> AGENTS.md` and `.claude -> .agents`
- All existing Claude Code functionality preserved via symlinks
- Skill files follow agentskills.io SKILL.md frontmatter format
- Templates render to new paths
- Existing tests pass