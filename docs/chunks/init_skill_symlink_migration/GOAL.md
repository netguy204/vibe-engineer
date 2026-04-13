---
status: HISTORICAL
ticket: null
parent_chunk: agentskills_migration
code_paths:
- src/project.py
- tests/test_project.py
- tests/test_init.py
code_references:
- ref: src/project.py#_is_ve_generated_file
  implements: "Helper that detects VE-generated command files via AUTO-GENERATED sentinel"
- ref: src/project.py#Project::_init_skills
  implements: "Updated elif branch that replaces VE-generated regular files with symlinks"
- ref: tests/test_project.py#TestInitSkillsSymlinkMigration
  implements: "Tests for both migration paths (VE-generated replacement and user-authored skip)"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: implements
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- board_watch_reconnect_fix
---

# Chunk Goal

## Minor Goal

Improve `ve init`'s skill symlink migration so that pre-existing regular files
in `.claude/commands/` are automatically replaced with symlinks pointing to
`.agents/skills/<name>/SKILL.md`, instead of silently skipping them with a
warning.

### Context

The `agentskills_migration` chunk moved skill storage from `.claude/commands/`
to `.agents/skills/`. For backwards compatibility, `ve init` creates symlinks
in `.claude/commands/` pointing to the new locations. However, if the project
already has regular files at those paths (from a pre-migration install), the
current code at `src/project.py:250-254` skips symlink creation and emits a
warning. This leaves the project in a broken state where `.claude/commands/`
contains stale regular files instead of symlinks to current skills.

### What needs to change

In `Project._init_skills()` (`src/project.py`), when a regular file exists at
the symlink target path:

1. **Compare content** — read the regular file and the skill source. If the
   regular file content matches the rendered skill (or is a known VE-generated
   file based on the `AUTO-GENERATED` header), it's safe to replace.
2. **Replace with symlink** — delete the regular file and create the symlink.
3. **Warn on unknown files** — if the file doesn't look VE-generated (no
   auto-generated header, content doesn't match), warn and skip as today. This
   protects user-authored command files from accidental deletion.

### Key constraint

Only replace files that VE itself generated. User-authored `.claude/commands/`
files must never be silently deleted.

## Success Criteria

- `ve init` on a project with pre-existing VE-generated `.claude/commands/*.md`
  regular files replaces them with symlinks
- `ve init` on a project with user-authored `.claude/commands/*.md` files warns
  and skips (preserves current behavior for non-VE files)
- Detection uses the `AUTO-GENERATED` header comment present in all VE-rendered
  command files
- Existing tests pass; new tests cover both migration paths
- The warnings output distinguishes "replaced regular file with symlink" from
  "skipped user-authored file"

## Relationship to Parent

Parent chunk `agentskills_migration` implemented the `.agents/skills/` layout
and backwards-compat symlinks. The symlink creation logic assumed a clean
starting state (no pre-existing files). This chunk fixes the migration path
for projects that already had VE-generated `.claude/commands/` files from
before the migration.