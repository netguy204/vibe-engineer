---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/template_system.py
- src/subsystems.py
- src/narratives.py
- src/project.py
- src/templates/subsystem/OVERVIEW.md.jinja2
- src/templates/narrative/OVERVIEW.md.jinja2
- src/templates/trunk/GOAL.md.jinja2
- src/templates/trunk/SPEC.md.jinja2
- src/templates/trunk/DECISIONS.md.jinja2
- src/templates/trunk/TESTING_PHILOSOPHY.md.jinja2
- src/templates/commands/chunk-create.md.jinja2
- src/templates/commands/chunk-plan.md.jinja2
- src/templates/commands/chunk-complete.md.jinja2
- src/templates/commands/chunk-update-references.md.jinja2
- src/templates/commands/chunks-resolve-references.md.jinja2
- src/templates/commands/chunk-implement.md.jinja2
- src/templates/commands/narrative-create.md.jinja2
- src/templates/commands/decision-create.md.jinja2
- src/templates/commands/subsystem-discover.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
- tests/test_template_system.py
- tests/test_project.py
- docs/subsystems/0001-template_system/OVERVIEW.md
code_references:
- ref: src/template_system.py#RenderResult
  implements: RenderResult dataclass tracking created/skipped/overwritten files
- ref: src/template_system.py#render_to_directory
  implements: Extended with overwrite parameter and RenderResult return type
- ref: src/subsystems.py#Subsystems::create_subsystem
  implements: Migrated to use render_to_directory with ActiveSubsystem context
- ref: src/narratives.py#Narratives::create_narrative
  implements: Migrated to use render_to_directory with ActiveNarrative context
- ref: src/project.py#Project::_init_trunk
  implements: Migrated from shutil.copy to render_to_directory (overwrite=False)
- ref: src/project.py#Project::_init_commands
  implements: Migrated from symlinks to render_to_directory (overwrite=True)
- ref: src/project.py#Project::_init_claude_md
  implements: Migrated from shutil.copy to render_template
- ref: tests/test_template_system.py#TestRenderToDirectory
  implements: Tests for RenderResult and overwrite behavior
- ref: tests/test_project.py#TestProjectInitIdempotency
  implements: Updated tests for new idempotent behavior
narrative: null
subsystems:
- subsystem_id: template_system
  relationship: implements
created_after:
- migrate_chunks_template
---

# Chunk Goal

## Minor Goal

Complete the template_system consolidation by migrating the remaining three modules
to use the canonical `template_system.py`:

1. **Migrate subsystems.py** - Replace duplicate `render_template` with import from `template_system`
2. **Migrate narratives.py** - Replace duplicate `render_template` with import from `template_system`
3. **Migrate project.py** - Replace `shutil.copy`/symlink approach with template rendering

This chunk resolves all NON_COMPLIANT code references in the template_system subsystem,
transitioning it from REFACTORING to STABLE status.

### Key Requirement: Idempotent File Overwrite Policy

The `render_to_directory` function needs an overwrite policy to support `ve init` idempotency:

- **Trunk documents (`docs/trunk/`)** - NEVER overwrite if they exist (user content)
- **CLAUDE.md** - NEVER overwrite if it exists (user content)
- **Commands (`.claude/commands/`)** - ALWAYS overwrite (managed templates that evolve)

This requires extending `render_to_directory` (or creating a variant) that accepts an
`overwrite` parameter:
- `overwrite=False` (default): Skip files that already exist
- `overwrite=True`: Always write, replacing existing files

### Rich Return Type

The current `render_to_directory` returns `list[pathlib.Path]` of created files. With the
overwrite policy, it should return a richer result type (similar to `project.py`'s `InitResult`):

```python
@dataclass
class RenderResult:
    created: list[pathlib.Path]    # Files that didn't exist and were created
    skipped: list[pathlib.Path]    # Files that existed and were not overwritten
    overwritten: list[pathlib.Path] # Files that existed and were replaced
```

This provides visibility into what happened during rendering.

### Template Suffix Migration

The trunk and commands templates must be renamed with `.jinja2` suffix to comply with
the template system invariant. While these templates currently have no dynamic content,
they will receive the `project` context variable, enabling future use of includes and
project-level variables.

### Symlink Removal

The current `_init_commands` creates symlinks (with copy fallback) for development
convenience. This approach is being removed in favor of full template rendering, which
enables command templates to use Jinja2 features (includes, variables, filters). Commands
will be rendered files, not symlinks.

## Success Criteria

1. **No duplicate render_template functions** - `src/subsystems.py` and `src/narratives.py`
   no longer contain local `render_template` functions

2. **project.py uses template_system** - `_init_trunk`, `_init_commands`, and `_init_claude_md`
   use `render_to_directory` or `render_template` instead of `shutil.copy`

3. **Idempotency preserved** - Running `ve init` twice produces the same result:
   - Trunk documents created on first run, skipped on second
   - CLAUDE.md created on first run, skipped on second
   - Commands are always updated to latest templates

4. **Templates renamed** - `src/templates/trunk/*.md` and `src/templates/commands/*.md`
   renamed to `*.md.jinja2`

5. **Subsystem updated** - All NON_COMPLIANT references in `docs/subsystems/0001-template_system/OVERVIEW.md`
   are marked COMPLIANT and status changed to STABLE

6. **Tests pass** - All existing tests continue to pass