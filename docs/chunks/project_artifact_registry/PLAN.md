<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk expands the `Project` class in `src/project.py` into a unified artifact registry by adding lazy-loaded properties for all artifact manager types. This is a pure structural refactoring that follows the existing pattern established by the `chunks` property.

**High-level strategy:**

1. Add `_narratives`, `_investigations`, `_subsystems`, and `_friction` private fields to `Project.__init__`
2. Add corresponding `@property` methods that lazily instantiate the managers
3. Refactor `Chunks.list_proposed_chunks()` to accept a `Project` instance instead of three separate manager parameters
4. Refactor `IntegrityValidator.__init__` to accept or construct a `Project` and access managers through its properties
5. Update all call sites that currently pass separate managers or construct their own managers

**Key design decisions:**

- Follow the identical `_field` / `@property` pattern used by `chunks` for consistency
- Import artifact managers at module level since they're already imported elsewhere (no circular import issues)
- Keep backward compatibility for CLI call sites by updating them to use `Project`

This approach aligns with the docs/subsystems/workflow_artifacts pattern for manager classes.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow artifact manager pattern. The `Project` class becomes a unified registry that provides access to all manager instances (`Chunks`, `Narratives`, `Investigations`, `Subsystems`, `Friction`). This is consistent with the subsystem's intent of providing unified structural patterns for workflow artifacts.

## Sequence

### Step 1: Add lazy-loaded manager properties to Project

Add private fields and corresponding lazy-loaded properties to the `Project` class for all artifact manager types:

- `_narratives` / `narratives` → `Narratives`
- `_investigations` / `investigations` → `Investigations`
- `_subsystems` / `subsystems` → `Subsystems`
- `_friction` / `friction` → `Friction`

Follow the exact pattern used by `_chunks` / `chunks`:

```python
@property
def narratives(self) -> Narratives:
    """Lazily instantiate and return a Narratives instance for this project."""
    if self._narratives is None:
        self._narratives = Narratives(self.project_dir)
    return self._narratives
```

Location: `src/project.py`

### Step 2: Update imports in project.py

Add imports for the new manager classes at the top of `project.py`:

```python
from narratives import Narratives
from investigations import Investigations
from subsystems import Subsystems
from friction import Friction
```

Location: `src/project.py`

### Step 3: Refactor Chunks.list_proposed_chunks signature

Change `Chunks.list_proposed_chunks()` to accept a `Project` instance instead of three separate manager parameters:

**Before:**
```python
def list_proposed_chunks(
    self,
    investigations: Investigations,
    narratives: Narratives,
    subsystems: Subsystems,
) -> list[dict]:
```

**After:**
```python
def list_proposed_chunks(
    self,
    project: Project,
) -> list[dict]:
```

Update the method body to access managers via `project.investigations`, `project.narratives`, `project.subsystems`.

Note: Import `Project` inside the method to avoid circular import (Chunks is imported by Project).

Location: `src/chunks.py`

### Step 4: Refactor IntegrityValidator.__init__

Change `IntegrityValidator.__init__` to accept or construct a `Project` instance and access all managers through its properties:

**Before:**
```python
def __init__(self, project_dir: pathlib.Path):
    self.project_dir = pathlib.Path(project_dir)
    self.chunks = Chunks(self.project_dir)
    self.narratives = Narratives(self.project_dir)
    self.investigations = Investigations(self.project_dir)
    self.subsystems = Subsystems(self.project_dir)
    self.friction = Friction(self.project_dir)
```

**After:**
```python
def __init__(self, project_dir: pathlib.Path, project: Project | None = None):
    self.project_dir = pathlib.Path(project_dir)
    if project is None:
        from project import Project
        project = Project(self.project_dir)
    self._project = project
    # Access managers via project properties
    self.chunks = self._project.chunks
    self.narratives = self._project.narratives
    self.investigations = self._project.investigations
    self.subsystems = self._project.subsystems
    self.friction = self._project.friction
```

This maintains backward compatibility (existing callers that pass only `project_dir` still work) while allowing callers that already have a `Project` instance to pass it directly.

Location: `src/integrity.py`

### Step 5: Update call sites in cli/chunk.py

Update `list_proposed_chunks_cmd` in `src/cli/chunk.py` to use `Project` instead of constructing separate managers:

**Before:**
```python
chunks = Chunks(project_dir)
investigations = Investigations(project_dir)
narratives = Narratives(project_dir)
subsystems_mgr = Subsystems(project_dir)

proposed = chunks.list_proposed_chunks(investigations, narratives, subsystems_mgr)
```

**After:**
```python
from project import Project

project = Project(project_dir)
proposed = project.chunks.list_proposed_chunks(project)
```

Location: `src/cli/chunk.py`

### Step 6: Update call sites in task_utils.py

Update `_list_task_proposed_chunks` in `src/task_utils.py` to use `Project` for both the external repo and project repos:

**Before:**
```python
chunks = Chunks(external_repo_path)
investigations = Investigations(external_repo_path)
narratives = Narratives(external_repo_path)
subsystems = Subsystems(external_repo_path)

external_proposed = chunks.list_proposed_chunks(investigations, narratives, subsystems)
```

**After:**
```python
from project import Project

external_project = Project(external_repo_path)
external_proposed = external_project.chunks.list_proposed_chunks(external_project)
```

Apply the same pattern for the project repos loop.

Location: `src/task_utils.py`

### Step 7: Add tests for new Project properties

Add tests to `tests/test_project.py` for the new lazy-loaded properties, following the existing pattern for `chunks`:

1. `test_narratives_property_returns_narratives_instance` - Verify type and project_dir
2. `test_narratives_property_is_lazy` - Verify `_narratives` is None until accessed
3. `test_narratives_property_returns_same_instance` - Verify memoization

Repeat for `investigations`, `subsystems`, and `friction` properties.

Location: `tests/test_project.py`

### Step 8: Update GOAL.md code_paths

Update the chunk's `code_paths` frontmatter field with the files touched:

```yaml
code_paths:
- src/project.py
- src/chunks.py
- src/integrity.py
- src/cli/chunk.py
- src/task_utils.py
- tests/test_project.py
```

Location: `docs/chunks/project_artifact_registry/GOAL.md`

### Step 9: Run tests and verify

Run the full test suite to verify no behavioral changes:

```bash
uv run pytest tests/
```

All existing tests should pass without modification to assertions.

## Dependencies

- **models_subpackage** (GOAL.md depends_on): The models subpackage should be complete so imports from `models/` work correctly. The models subpackage has already been implemented (verified by `ls src/models/`).

## Risks and Open Questions

1. **Circular imports**: `Project` imports `Chunks`, and `Chunks.list_proposed_chunks` needs access to `Project`. Mitigated by using a local import inside the method (`from project import Project`).

2. **IntegrityValidator backward compatibility**: The change to accept an optional `Project` parameter maintains backward compatibility. Existing callers that pass only `project_dir` will continue to work.

3. **Performance**: Lazy loading means managers are only instantiated when accessed. This is the existing pattern and should not introduce performance regressions.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->