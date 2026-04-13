

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix is surgical: modify the `elif link_path.exists():` branch in
`Project._init_skills()` to distinguish VE-generated regular files from
user-authored ones, replacing the former and warning on the latter.

Detection is done via a module-level helper `_is_ve_generated_file(path)` that
looks for the `AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY` sentinel string
present in every file rendered from a command template (injected via
`src/templates/commands/partials/auto-generated-header.md.jinja2`).

Tests follow TDD: write failing tests first (for the migration path and the
skip-user-authored path), then implement, then verify both pass. All new tests
go in `tests/test_project.py` under a dedicated `TestInitSkillsSymlinkMigration`
class, consistent with the existing test organization.

No new decisions require DECISIONS.md entries — this is a targeted migration
fix, not an architectural choice.

## Subsystem Considerations

- **docs/subsystems/template_system** (relationship: uses) — The AUTO-GENERATED
  sentinel we detect is emitted by the template system's
  `auto-generated-header.md.jinja2` partial. No pattern deviation; this chunk
  simply reads an output that the template system produces.

## Sequence

### Step 1: Write failing tests for the two migration paths

Add a new test class `TestInitSkillsSymlinkMigration` to
`tests/test_project.py`. Each test sets up the `.claude/commands/` directory
manually before calling `project.init()`, simulating the pre-migration state.

**Test A** — VE-generated regular file is replaced with a symlink:
- Create `.claude/commands/` and write a regular file at
  `.claude/commands/chunk-create.md` whose content includes the string
  `AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY` (as all VE-rendered command
  files do).
- Run `project.init()`.
- Assert that `.claude/commands/chunk-create.md` is now a symlink.
- Assert that the symlink resolves to `.agents/skills/chunk-create/SKILL.md`.
- Assert that the path appears in `result.created`.
- Assert that no "user-authored" warning was emitted.

**Test B** — User-authored regular file is left alone with a warning:
- Create `.claude/commands/` and write a regular file at
  `.claude/commands/chunk-create.md` whose content does **not** contain the
  AUTO-GENERATED sentinel (user wrote this themselves).
- Run `project.init()`.
- Assert that `.claude/commands/chunk-create.md` is still a regular file (not
  a symlink).
- Assert that the file content is unchanged.
- Assert that `result.warnings` contains a message distinguishing this as a
  user-authored file skip.
- Assert the path does **not** appear in `result.created`.

**Test C** — Warning messages are distinguishable:
- After a VE-generated replacement, verify no "user-authored" language appears
  in warnings for that file.
- After a user-authored skip, verify the warning message does not say
  "replaced" and does say something indicating user content preservation.

Run `uv run pytest tests/test_project.py::TestInitSkillsSymlinkMigration` —
all three tests should **fail** (function not yet updated). This confirms the
red phase.

### Step 2: Add `_is_ve_generated_file()` module-level helper

Location: `src/project.py`, immediately before the `Project` class definition
(near the other module-level constants/functions like `parse_markers`).

```python
# Chunk: docs/chunks/init_skill_symlink_migration - VE-generated file detection for symlink migration
def _is_ve_generated_file(path: pathlib.Path) -> bool:
    """Return True if the file appears to be a VE-generated command file.

    Detects the AUTO-GENERATED header comment present in all VE-rendered
    command files (injected via auto-generated-header.md.jinja2). Used to
    determine whether a regular file in .claude/commands/ is safe to replace
    with a symlink during migration.

    Returns False for any file that cannot be read (binary, permission error,
    encoding error) — treat unreadable files as user-authored to avoid data loss.
    """
    try:
        content = path.read_text(encoding="utf-8")
        return "AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY" in content
    except (OSError, UnicodeDecodeError):
        return False
```

### Step 3: Update the `elif link_path.exists():` branch in `_init_skills()`

Location: `src/project.py`, lines 250–254 (current behaviour).

Replace:
```python
elif link_path.exists():
    # Regular file exists with same name - skip to avoid data loss, warn
    result.warnings.append(
        f".claude/commands/{skill_name}.md exists as a regular file, skipping symlink"
    )
```

With:
```python
elif link_path.exists():
    # Regular file exists - check if it's a VE-generated file we can safely replace
    if _is_ve_generated_file(link_path):
        # VE-generated file: replace with symlink (migration from pre-agentskills layout)
        link_path.unlink()
        link_path.symlink_to(relative_target)
        result.created.append(f".claude/commands/{skill_name}.md")
    else:
        # User-authored file: warn and skip to avoid data loss
        result.warnings.append(
            f".claude/commands/{skill_name}.md is a user-authored file; skipping symlink creation"
        )
```

Add a backreference comment immediately before the `elif` to aid future
archaeologists:
```python
# Chunk: docs/chunks/init_skill_symlink_migration - Migrate VE-generated regular files to symlinks
```

### Step 4: Run the full test suite

```bash
uv run pytest tests/
```

All tests should pass — both the new `TestInitSkillsSymlinkMigration` tests
(now green) and all pre-existing tests (no regression).

If any test fails, diagnose and fix before proceeding.

## Dependencies

None — this is a pure modification of existing code with no new libraries or
infrastructure.

## Risks and Open Questions

- **Encoding edge cases**: If a `.claude/commands/` file is binary or
  non-UTF-8, `read_text()` will raise `UnicodeDecodeError`. The helper returns
  `False` in that case, treating it as user-authored. This is the safe
  default.
- **Content drift**: Future template changes could alter the AUTO-GENERATED
  sentinel string. If the sentinel is ever renamed, the detection would
  silently stop migrating old files. The sentinel is defined in
  `src/templates/commands/partials/auto-generated-header.md.jinja2` and should
  be treated as stable.
- **Partial writes**: If `link_path.unlink()` succeeds but `symlink_to()` fails
  (e.g., permission error), the file is lost. This is an acceptable risk —
  the same failure mode exists when creating fresh symlinks, and the skill
  content is always recoverable via `ve init` on any clean directory.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
