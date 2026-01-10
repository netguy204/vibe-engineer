# Implementation Plan

## Approach

Create a new `src/template_system.py` module that provides a unified Jinja2
template rendering system. The module will:

1. Use Jinja2's `Environment` class with a `FileSystemLoader` configured for each
   template collection (chunk, subsystem, narrative, commands, trunk)
2. Provide dataclasses for context objects (`ActiveChunk`, `ActiveNarrative`,
   `ActiveSubsystem`) with computed path properties
3. Provide a `TemplateContext` class that holds the project-level context with
   one active artifact at a time
4. Support includes via `partials/` subdirectories within each collection
5. Handle `.jinja2` suffix stripping when writing rendered output

This follows docs/trunk/TESTING_PHILOSOPHY.md by writing tests first. We'll use
TDD to implement each component.

## Subsystem Considerations

- **docs/subsystems/0001-template_system** (REFACTORING): This chunk IMPLEMENTS
  the canonical template_system module, which is the foundational piece for the
  entire subsystem. Since the subsystem is in REFACTORING status, we are actively
  consolidating—but this chunk only creates the new module; migration of existing
  code happens in subsequent chunks.

## Sequence

### Step 1: Write failing tests for context dataclasses

Create `tests/test_template_system.py` with tests for:
- `ActiveChunk` with `short_name`, `id`, `goal_path`, `plan_path`
- `ActiveNarrative` with `short_name`, `id`, `overview_path`
- `ActiveSubsystem` with `short_name`, `id`, `overview_path`
- Path properties return correct `pathlib.Path` objects relative to project root

Location: `tests/test_template_system.py`

### Step 2: Implement context dataclasses

Create the three dataclasses that represent active artifacts:

```python
@dataclass
class ActiveChunk:
    short_name: str
    id: str  # Full ID like "0023-canonical_template_module"
    _project_dir: pathlib.Path

    @property
    def goal_path(self) -> pathlib.Path:
        return self._project_dir / "docs" / "chunks" / self.id / "GOAL.md"

    @property
    def plan_path(self) -> pathlib.Path:
        return self._project_dir / "docs" / "chunks" / self.id / "PLAN.md"
```

Similar patterns for `ActiveNarrative` and `ActiveSubsystem` with `overview_path`.

Location: `src/template_system.py`

### Step 3: Write failing tests for TemplateContext

Add tests for the `TemplateContext` class:
- Can create with `active_chunk` only (others are None)
- Can create with `active_narrative` only
- Can create with `active_subsystem` only
- Raises error if more than one active artifact is set
- `as_dict()` method returns context suitable for Jinja2

Location: `tests/test_template_system.py`

### Step 4: Implement TemplateContext

Create the class that holds project-level context:

```python
@dataclass
class TemplateContext:
    active_chunk: ActiveChunk | None = None
    active_narrative: ActiveNarrative | None = None
    active_subsystem: ActiveSubsystem | None = None

    def __post_init__(self):
        count = sum(1 for x in [self.active_chunk, self.active_narrative,
                                 self.active_subsystem] if x is not None)
        if count > 1:
            raise ValueError("Only one active artifact allowed")

    def as_dict(self) -> dict:
        return {"project": self}
```

Location: `src/template_system.py`

### Step 5: Write failing tests for list_templates

Add tests for template enumeration:
- `list_templates("chunk")` returns template files in `src/templates/chunk/`
- Returns empty list for non-existent collection
- Does not include files in `partials/` subdirectory
- Works with both `.md` and future `.jinja2` suffixed files

Location: `tests/test_template_system.py`

### Step 6: Implement list_templates

Create function to enumerate templates in a collection:

```python
def list_templates(collection: str) -> list[str]:
    """List template files in a collection (excludes partials/)."""
    collection_dir = template_dir / collection
    if not collection_dir.exists():
        return []
    return [f.name for f in collection_dir.iterdir()
            if f.is_file() and not f.name.startswith(".")]
```

Location: `src/template_system.py`

### Step 7: Write failing tests for get_environment

Add tests for Jinja2 Environment creation:
- Environment loads templates from the specified collection
- Environment can resolve `{% include 'partials/foo.md' %}`
- Environment caches for performance (same collection returns same Environment)

Location: `tests/test_template_system.py`

### Step 8: Implement get_environment

Create function to get/cache Jinja2 Environment per collection:

```python
_environments: dict[str, jinja2.Environment] = {}

def get_environment(collection: str) -> jinja2.Environment:
    """Get or create a Jinja2 Environment for a template collection."""
    if collection not in _environments:
        collection_dir = template_dir / collection
        loader = jinja2.FileSystemLoader(str(collection_dir))
        _environments[collection] = jinja2.Environment(loader=loader)
    return _environments[collection]
```

Location: `src/template_system.py`

### Step 9: Write failing tests for render_template

Add tests for the core rendering function:
- Renders template with context variables
- Injects `TemplateContext` into render context
- Works with includes
- Raises appropriate error for missing templates

Location: `tests/test_template_system.py`

### Step 10: Implement render_template

Create the main rendering function:

```python
def render_template(
    collection: str,
    template_name: str,
    context: TemplateContext | None = None,
    **kwargs
) -> str:
    """Render a template from a collection with the given context."""
    env = get_environment(collection)
    template = env.get_template(template_name)

    render_context = {}
    if context:
        render_context.update(context.as_dict())
    render_context.update(kwargs)

    return template.render(**render_context)
```

Location: `src/template_system.py`

### Step 11: Write failing tests for render_to_directory

Add tests for directory rendering:
- Renders all templates in collection to destination directory
- Strips `.jinja2` suffix from output filenames
- Does not render files in `partials/` subdirectory
- Creates destination directory if needed
- Passes context to each template

Location: `tests/test_template_system.py`

### Step 12: Implement render_to_directory

Create function to render all templates in a collection:

```python
def render_to_directory(
    collection: str,
    dest_dir: pathlib.Path,
    context: TemplateContext | None = None,
    **kwargs
) -> list[pathlib.Path]:
    """Render all templates in a collection to a destination directory.

    Returns list of created file paths.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for template_name in list_templates(collection):
        # Strip .jinja2 suffix for output filename
        output_name = template_name
        if output_name.endswith(".jinja2"):
            output_name = output_name[:-7]  # Remove ".jinja2"

        rendered = render_template(collection, template_name, context, **kwargs)
        output_path = dest_dir / output_name
        output_path.write_text(rendered)
        created.append(output_path)

    return created
```

Location: `src/template_system.py`

### Step 13: Write integration tests

Add end-to-end tests that:
- Create a temporary test template with includes
- Render it with a full `TemplateContext`
- Verify the output contains expected content from both main template and partial
- Test error handling for invalid collections

Location: `tests/test_template_system.py`

### Step 14: Run full test suite and fix any issues

Execute `pytest tests/` to ensure:
- All new tests pass
- No regressions in existing tests
- Coverage is adequate for success criteria

## Dependencies

- **jinja2**: Already a dependency (used by existing `render_template` functions)
- No new external dependencies required

## Risks and Open Questions

1. **Environment caching**: The `_environments` dict caches forever. This is fine
   for CLI usage but could cause issues in long-running processes. Acceptable for
   now since the CLI is short-lived.

2. **Template discovery order**: `list_templates` uses `iterdir()` which doesn't
   guarantee order. This shouldn't matter for rendering but could affect tests.
   Consider sorting if determinism is needed.

3. **Partial discovery**: Current plan excludes only `partials/` subdirectory.
   Should other directories be excluded? For now, we keep it simple.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->