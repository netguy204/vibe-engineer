---
discovered_by: audit batch 11a
discovered_at: 2026-04-26T02:39:29Z
severity: medium
status: open
artifacts:
  - docs/chunks/project_init_command/GOAL.md
---

# Claim

`docs/chunks/project_init_command/GOAL.md` makes several specific structural claims:

1. "**Set up Claude Code commands** - Create the `.claude/commands/` directory and symlink all command templates from `src/templates/commands/` into it."
2. "Symlinks in `.claude/commands/` point to the ve package's `src/templates/commands/` directory (so they update automatically when ve is upgraded)"
3. "**Create CLAUDE.md** - **Copy** the `src/templates/CLAUDE.md` template to the project root."

# Reality

The init flow has been substantially restructured by later chunks. The current `Project._init_skills` (`src/project.py:213-294`) does:

- Renders skill templates to `.agents/skills/<name>/SKILL.md` (not `.claude/commands/`).
- Creates per-file symlinks in `.claude/commands/<name>.md` pointing at `../../.agents/skills/<name>/SKILL.md` — i.e. into the local `.agents/skills/` tree, **not** into `src/templates/commands/` in the ve package.
- Migrates VE-generated regular files in `.claude/commands/` to symlinks (per `init_skill_symlink_migration`).
- Cleans up stale symlinks no longer corresponding to active skills.

This means GOAL claims (1) and (2) are now both false in their structural details:
- The symlinks do **not** target `src/templates/commands/`.
- They will **not** update automatically when the ve package is upgraded — they target locally rendered skill files.

For claim (3), CLAUDE.md is **rendered from a Jinja2 template** (`src/templates/claude/CLAUDE.md.jinja2`), not "copied." The template path itself differs from what the GOAL says (`src/templates/CLAUDE.md`). There is also a new `_init_agents_md` step that renders `AGENTS.md` to the project root — entirely absent from the GOAL.

The chunk's foundational intent (`ve init` bootstraps the workflow) remains valid, and the chunk is still the named owner of `Project.init`, `_init_trunk`, `InitResult`, and the CLAUDE.md Jinja2 template per backreferences in `src/project.py:5`, `src/cli/init_cmd.py:6`, `src/templates/claude/CLAUDE.md.jinja2:1`, `tests/test_init.py:2`, `tests/test_project.py:2`. Successor chunks (`init_skill_symlink_migration`, `narrative_cli_commands`, the agentskills migration chunks) own the deltas. Did not historicalize because the chunk is still uniquely the canonical home for the `Project.init` orchestration contract.

# Workaround

None needed for current work; readers should follow the `# Chunk:` backreferences in `src/project.py` to find the successor chunks owning skill layout, AGENTS.md, and symlink migration.

# Fix paths

1. **Update GOAL.md prose** to describe the current behavior: skills render to `.agents/skills/`, symlinks in `.claude/commands/` target local skill files (not the ve package), CLAUDE.md is rendered (not copied) from the Jinja2 template, AGENTS.md is also rendered. Preferred — preserves the chunk as the canonical init-orchestration owner while truthifying its claims.
2. **Mark this chunk historical and let the successor chunks own the contracts.** Less preferred because no single successor uniquely owns the top-level `Project.init` orchestration story.
