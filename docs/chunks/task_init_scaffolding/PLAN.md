<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk enhances `ve task init` to generate Claude Code scaffolding files alongside `.ve-task.yaml`. The approach follows the existing patterns in the codebase:

1. **Create a new task CLAUDE.md template** (`src/templates/task/CLAUDE.md.jinja2`) based on the lean prototype from the investigation (~30 lines). This template uses Jinja2 variables `external_artifact_repo` and `projects` to render task-specific content.

2. **Add conditional blocks to command templates** using Jinja2's `{% if task_context %}...{% else %}...{% endif %}` pattern. This allows the same templates to serve both project and task contexts with appropriate guidance.

3. **Extend TaskInit to render scaffolding** by adding new methods to generate CLAUDE.md and render `.claude/commands/` from templates, following the same patterns used in `src/project.py`.

4. **Create a TaskContext dataclass** in `template_system.py` to provide task-specific template context, analogous to how `TemplateContext` works for project contexts.

The implementation leverages the established template_system subsystem (STABLE status), which provides `render_template`, `render_to_directory`, and related utilities.

Per DEC-004 (markdown references relative to project root), file paths in documentation are relative to project root.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template subsystem's established patterns:
  - `render_template()` and `render_to_directory()` for template rendering
  - `.jinja2` suffix convention for template files
  - Template collections organized in `src/templates/{collection}/`

  Since the subsystem is STABLE, we follow its patterns exactly without attempting modifications.

## Sequence

### Step 1: Create task CLAUDE.md template

Create `src/templates/task/CLAUDE.md.jinja2` based on the lean prototype from `docs/investigations/task_agent_experience/prototypes/CLAUDE.md.lean.template`.

The template should:
- Use Jinja2 syntax (not Mustache as in prototype)
- Accept `external_artifact_repo` (string) and `projects` (list of strings)
- Be approximately 30 lines
- Provide essential orientation: project list, where commands work, navigation basics
- Defer detailed workflow guidance to slash commands

Location: `src/templates/task/CLAUDE.md.jinja2`

### Step 2: Add TaskContext dataclass to template_system

Extend `src/template_system.py` with a `TaskContext` dataclass to hold task-specific template context:

```python
@dataclass
class TaskContext:
    """Holds task-level context for template rendering."""
    external_artifact_repo: str
    projects: list[str]
    task_context: bool = True  # Flag for conditional blocks in templates

    def as_dict(self) -> dict:
        """Return context as dict suitable for Jinja2 rendering."""
        return {
            "external_artifact_repo": self.external_artifact_repo,
            "projects": self.projects,
            "task_context": self.task_context,
        }
```

This follows the pattern of existing `TemplateContext` but serves task contexts.

Location: `src/template_system.py`

### Step 3: Add conditional blocks to command templates

Update command templates to include task-aware content using Jinja2 conditionals:

For `/chunk-create` (`src/templates/commands/chunk-create.md.jinja2`):
- Add explanation that in task context, artifacts are created in the external repo
- Note that external.yaml references are created in participating projects

For `/chunk-implement` (`src/templates/commands/chunk-implement.md.jinja2`):
- Add note that implementation may span multiple participating projects in task context

For `/chunk-plan` (`src/templates/commands/chunk-plan.md.jinja2`):
- Works from task root, PLAN.md created in external repo's chunk directory

For `/chunk-complete` (`src/templates/commands/chunk-complete.md.jinja2`):
- Note about collecting code_references from all participating projects in task context

For `/narrative-create`, `/subsystem-discover`, `/investigation-create`:
- Similar pattern: artifacts created in external repo in task context

Use the pattern:
```jinja2
{% if task_context %}
**Task Context:** This command creates artifacts in the external artifact repo
(`{{ external_artifact_repo }}`). External references will be created in
participating projects.
{% endif %}
```

Locations: All files in `src/templates/commands/`

### Step 4: Extend TaskInit with scaffolding generation

Add methods to `src/task_init.py`:

1. `_render_claude_md()` - Renders the task CLAUDE.md template to task root
2. `_render_commands()` - Renders command templates to `.claude/commands/` with task context

Modify `execute()` to call these new methods after creating `.ve-task.yaml`.

The implementation should:
- Import `render_template`, `render_to_directory`, and `TaskContext` from `template_system`
- Create `TaskContext` with config values
- Render templates with task context (task_context=True)

Location: `src/task_init.py`

### Step 5: Update TaskInitResult

Extend `TaskInitResult` dataclass to include information about scaffolding files:

```python
@dataclass
class TaskInitResult:
    config_path: Path
    external_repo: str
    projects: list[str]
    created_files: list[str] = field(default_factory=list)  # New
```

Location: `src/task_init.py`

### Step 6: Regenerate project .claude/commands/ with task_context=False

To ensure existing projects get commands with the conditional blocks resolved for project context, we need to ensure `ve init` renders commands with `task_context=False`.

Modify `src/project.py#_init_commands()` to pass `task_context=False` when rendering:

```python
render_result = render_to_directory(
    "commands", commands_dir, context=context, overwrite=True, task_context=False
)
```

This ensures the project-context versions don't have any `{% if task_context %}` remnants.

Location: `src/project.py`

### Step 7: Write tests for CLAUDE.md generation

Create test cases verifying:
- `ve task init` creates CLAUDE.md in task directory
- CLAUDE.md contains external_artifact_repo from config
- CLAUDE.md contains project list from config
- Content is rendered from template (not a copy of template source)

Follow TDD: write failing tests first, then implement.

Location: `tests/test_task_init.py`

### Step 8: Write tests for command rendering

Create test cases verifying:
- `ve task init` creates `.claude/commands/` directory
- All command templates are rendered (chunk-create.md, etc.)
- Commands contain task-context specific content (conditional blocks resolved)
- Commands reference external_artifact_repo from config

Follow TDD: write failing tests first, then implement.

Location: `tests/test_task_init.py`

### Step 9: Write tests for conditional block processing

Create test cases verifying:
- In task context: task-specific content is present
- In project context: task-specific content is absent
- Templates render without errors in both contexts

This may require a new test file or additions to existing template tests.

Location: `tests/test_template_system.py` or `tests/test_task_init.py`

### Step 10: Run tests and update SPEC.md

1. Run full test suite: `uv run pytest tests/`
2. Fix any failures
3. Update `docs/trunk/SPEC.md` to document:
   - Task directory structure now includes CLAUDE.md and `.claude/commands/`
   - `ve task init` postconditions include scaffolding file creation

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:

```python
# Chunk: docs/chunks/task_init_scaffolding - Task CLAUDE.md and commands scaffolding
# Subsystem: docs/subsystems/template_system - Uses template rendering
```

## Dependencies

- **template_system subsystem (STABLE)**: Required for `render_template`, `render_to_directory`, and template collection patterns
- **Existing command templates**: Templates in `src/templates/commands/` that will receive conditional blocks
- **task_init.py**: The existing TaskInit class that will be extended

## Risks and Open Questions

1. **Conditional block syntax in rendered output**: When rendering commands for project context (`task_context=False`), Jinja2 should completely omit the conditional blocks. Need to verify the templates render cleanly in both contexts.

2. **Template variable availability**: Command templates currently render with `TemplateContext` which has project-level context. Need to ensure `task_context` variable is available even when not in task mode (as `False` or undefined).

3. **Idempotency of scaffolding creation**: The current `ve task init` fails if `.ve-task.yaml` exists. The new scaffolding generation should follow the same pattern (fail if already exists rather than silently overwrite).

4. **Test helper reuse**: Per TESTING_PHILOSOPHY.md, should check `conftest.py` for existing helpers before creating new ones. The `setup_task_directory` helper already exists and should be extended rather than duplicated.

## Deviations

<!-- Populate during implementation -->