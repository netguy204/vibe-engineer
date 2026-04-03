


<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Migrate VE's agent instruction and skill file structure from Claude-specific
paths to the agentskills.io open standard. The migration is purely structural:
skills behave identically, but their storage follows the agentskills.io
directory convention (`.agents/skills/<name>/SKILL.md`) and the canonical
instructions file becomes `AGENTS.md`.

Backwards compatibility with Claude Code is maintained via symlinks:
- `CLAUDE.md` → `AGENTS.md` (file symlink)
- `.claude/commands/<name>.md` → `../../.agents/skills/<name>/SKILL.md` (per-file symlinks)

The per-file symlink approach (rather than `.claude -> .agents`) is necessary
because the directory structures differ: Claude Code expects flat files at
`.claude/commands/<name>.md`, while agentskills.io expects nested directories
at `.agents/skills/<name>/SKILL.md`.

**Key design decisions:**
- Template frontmatter gains a `name` field matching the agentskills.io spec
  (lowercase, hyphens, must match parent directory name)
- The `allowed-tools` field is preserved as-is (it's an experimental
  agentskills.io field)
- `render_to_directory` is extended with a `skill_layout` mode that creates
  `<name>/SKILL.md` structure instead of flat `<name>.md` files
- The existing marker system for managed content in CLAUDE.md/AGENTS.md works
  transparently through symlinks (read/write operations follow symlinks)

Testing follows TESTING_PHILOSOPHY.md: tests verify side effects (files
created, symlinks point correctly, content renders) not template prose.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk IMPLEMENTS changes
  to the template rendering pipeline (new `skill_layout` parameter in
  `render_to_directory`). The subsystem is STABLE, so changes should be
  minimal and consistent with existing patterns.
- **docs/subsystems/cross_repo_operations** (documented): This chunk USES the
  cross-repo task init system. Changes to `task_init.py` must follow the same
  migration pattern.

## Sequence

### Step 1: Add `name` field to template frontmatter

Each command template in `src/templates/commands/` needs a `name` field in its
YAML frontmatter. The name is derived from the template filename (strip
`.md.jinja2`, which already yields a lowercase hyphenated string matching the
agentskills.io naming rules).

Example change for `chunk-create.md.jinja2`:
```yaml
---
name: chunk-create
description: Create a new chunk of work...
---
```

Templates with `allowed-tools` keep that field (it maps to agentskills.io's
experimental `allowed-tools` field).

Location: `src/templates/commands/*.md.jinja2` (all ~36 templates)

Validation: Each `name` field must match the filename stem (the part before
`.md.jinja2`). This is enforced by convention, not runtime code.

### Step 2: Extend `render_to_directory` with `skill_layout` parameter

Add a `skill_layout: bool = False` parameter to `render_to_directory()` in
`src/template_system.py`. When `True`, each template renders to
`dest_dir/<name>/SKILL.md` instead of `dest_dir/<name>.md`.

The `<name>` is derived by stripping `.jinja2` and then `.md` from the
template filename (e.g., `chunk-create.md.jinja2` → `chunk-create`).

```python
def render_to_directory(
    collection: str,
    dest_dir: pathlib.Path,
    context: TemplateContext | None = None,
    overwrite: bool = False,
    skill_layout: bool = False,  # NEW
    **kwargs,
) -> RenderResult:
```

When `skill_layout=True`:
- Create subdirectory `dest_dir/<name>/`
- Write rendered content to `dest_dir/<name>/SKILL.md`
- The `<name>` is the template filename without `.md.jinja2`

Location: `src/template_system.py`

### Step 3: Update `_init_commands` → `_init_skills` in Project

Rename `_init_commands()` to `_init_skills()` and change it to:

1. Render templates to `.agents/skills/` using `skill_layout=True`
2. Create `.claude/commands/` directory
3. Create per-file symlinks: `.claude/commands/<name>.md` →
   `../../.agents/skills/<name>/SKILL.md`
4. Clean up stale symlinks in `.claude/commands/` that no longer correspond to
   skills (handle skill renames/removals across ve versions)
5. Clean up stale flat files in `.agents/skills/` from pre-migration (if any
   exist, though unlikely for this initial migration)

The symlink target uses a relative path (`../../.agents/skills/<name>/SKILL.md`)
so the project remains relocatable.

Location: `src/project.py`

### Step 4: Update `_init_claude_md` → `_init_agents_md` in Project

Rename `_init_claude_md()` to `_init_agents_md()` and change its behavior:

**Case A: Fresh init (no AGENTS.md, no CLAUDE.md)**
1. Render template to `AGENTS.md` (with markers)
2. Create symlink `CLAUDE.md` → `AGENTS.md`

**Case B: Existing CLAUDE.md as regular file (pre-migration project)**
1. Rename `CLAUDE.md` to `AGENTS.md` (preserves user content and markers)
2. Create symlink `CLAUDE.md` → `AGENTS.md`
3. Update managed content inside markers (same as current reinit behavior)

**Case C: AGENTS.md exists (already migrated)**
1. Update managed content inside markers (same as current behavior)
2. Ensure `CLAUDE.md` symlink exists and points to `AGENTS.md`

**Case D: CLAUDE.md is already a symlink to AGENTS.md**
1. Update managed content in AGENTS.md via markers
2. No symlink changes needed

The template collection name stays `"claude"` but the template file is renamed:
`src/templates/claude/CLAUDE.md.jinja2` → `src/templates/claude/AGENTS.md.jinja2`

The marker constants remain the same (`VE:MANAGED:START/END`).

Location: `src/project.py`, `src/templates/claude/`

### Step 5: Update `init()` method in Project

Update the `init()` method to call the renamed methods:
- `_init_skills()` instead of `_init_commands()`
- `_init_agents_md()` instead of `_init_claude_md()`

Location: `src/project.py`

### Step 6: Update task init to use new structure

Update `TaskInit` in `src/task_init.py`:

- `_render_commands()` → `_render_skills()`: Render to `.agents/skills/` with
  `skill_layout=True`, then create `.claude/commands/` symlinks
- `_render_claude_md()` → `_render_agents_md()`: Render to `AGENTS.md`, create
  `CLAUDE.md` → `AGENTS.md` symlink
- Template collection for task instructions changes from `"task"` to use
  `AGENTS.md.jinja2` (or the task template is similarly renamed)

Location: `src/task_init.py`

### Step 7: Update orchestrator worktree symlinks

Update `_setup_agent_environment_symlinks` in `src/orchestrator/worktree.py`
to reference the new canonical paths:

```python
symlink_targets = [
    (".ve-task.yaml", task_dir / ".ve-task.yaml"),
    ("AGENTS.md", task_dir / "AGENTS.md"),
    ("CLAUDE.md", task_dir / "CLAUDE.md"),   # May itself be a symlink
    (".agents", task_dir / ".agents"),
    (".claude", task_dir / ".claude"),         # May itself be a symlink
]
```

The key insight: if the task directory already has `CLAUDE.md` as a symlink to
`AGENTS.md`, creating a symlink to that symlink in the worktree still works
(symlinks chain correctly). So the orchestrator doesn't need special handling —
it just symlinks whatever exists.

Update `_cleanup_agent_environment_symlinks` to also clean up `AGENTS.md` and
`.agents` symlinks.

Location: `src/orchestrator/worktree.py`

### Step 8: Rename template file

Rename `src/templates/claude/CLAUDE.md.jinja2` to
`src/templates/claude/AGENTS.md.jinja2`. Update the auto-generated header
comment inside the template if it references `CLAUDE.md` by name.

The template's content doesn't change (it's still the VE-managed instructions
for agents). Only the filename and any self-references change.

Location: `src/templates/claude/`

### Step 9: Update tests

Update existing tests in `tests/test_project.py` and `tests/test_init.py`:

**test_project.py changes:**
- Tests for `_init_claude_md` → test `_init_agents_md` behavior
- Add tests for AGENTS.md creation with CLAUDE.md symlink
- Add test for migration case (existing CLAUDE.md → AGENTS.md + symlink)
- Tests for `_init_commands` → test `_init_skills` behavior
- Add tests that `.agents/skills/<name>/SKILL.md` files are created
- Add tests that `.claude/commands/<name>.md` symlinks point to correct targets
- Add tests that symlinks are relative (not absolute)

**test_init.py changes:**
- Update CLI integration tests to verify new file structure
- Verify both `.agents/skills/` and `.claude/commands/` exist after init

**test_template_system.py changes (if exists):**
- Add tests for `skill_layout=True` in `render_to_directory`

**test_task_init.py changes:**
- Update task init tests for new paths

Location: `tests/`

### Step 10: Update .gitignore if needed

Check if `.agents/` or any new paths need to be added to `.gitignore`
patterns. The `.agents/` directory IS committed (it contains skills), so no
gitignore changes are needed for that. But verify that the symlinks
(`CLAUDE.md`, `.claude/`) are handled correctly by git.

Note: Git handles symlinks natively — both the symlink itself and its target
will be committed. This means cloning the repo preserves the compatibility
layer without running `ve init`.

Location: `.gitignore` (likely no changes needed)

## Dependencies

- The agentskills.io specification at https://agentskills.io/specification
  defines the SKILL.md frontmatter format and directory structure.
- No new external libraries are needed.

## Risks and Open Questions

- **Symlink behavior on Windows**: Git on Windows may not preserve symlinks
  depending on configuration. This is a known limitation but acceptable since
  VE primarily targets macOS/Linux development environments.
- **Existing `.claude/` content**: If a user has manually added files to
  `.claude/commands/`, those files won't be affected by the symlink creation
  (symlinks only target skill names that VE manages). But if a user has a file
  with the same name as a VE skill, the symlink creation would need to handle
  the conflict. Plan: skip symlink creation for files that exist as regular
  files (not symlinks), and warn.
- **Task template rename**: The task-context CLAUDE.md template
  (`src/templates/task/CLAUDE.md.jinja2`) may also need renaming. Need to
  verify the task template structure during implementation.

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
-->
