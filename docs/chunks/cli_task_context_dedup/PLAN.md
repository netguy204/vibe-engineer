<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

We will introduce a **decorator pattern** that abstracts the task-context branching logic. The decorator will:

1. Check if the current `project_dir` is a task directory using `is_task_directory()`
2. If in task context: call the provided task handler with the relevant arguments
3. If not in task context: fall through to let the decorated function execute normally

The decorator approach is preferred over a context manager because:
- The branching pattern is at the function entry point, not mid-function
- Decorators integrate cleanly with Click's command decorators
- The pattern is pure routing logic (if-then-return), not resource management

**Strategy:**
1. Create a `@task_aware` decorator in `src/cli/utils.py` that handles the branching
2. The decorator takes a `task_handler` callable as its argument
3. Migrate each CLI command to use the decorator, removing manual `is_task_directory()` checks
4. Ensure existing behavior is preserved (task handlers are called when in task directory)

**Testing:**
- Add unit tests for the decorator in `tests/test_cli_utils.py`
- Existing CLI tests should pass without modification (proving behavioral equivalence)

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow artifact
  pattern. The `is_task_directory()` check is part of the task-aware command pattern
  documented in this subsystem. This chunk consolidates the boilerplate but preserves
  the underlying pattern.

No deviations discovered during analysis.

## Sequence

### Step 1: Design the task_aware decorator

Create the `task_aware` decorator in `src/cli/utils.py`. The decorator:

- Takes a `task_handler` callable as its required argument
- Returns a wrapper function that:
  1. Extracts `project_dir` from kwargs (defaulting to Path("."))
  2. Checks `is_task_directory(project_dir)`
  3. If True: calls `task_handler(project_dir, **kwargs)` and returns (early exit)
  4. If False: calls the original function normally

**Design considerations:**
- The decorator must preserve Click's introspection (use `functools.wraps`)
- Task handlers receive `project_dir` as first positional arg plus all kwargs
- Existing task handlers already expect this signature

**Signature:**
```python
def task_aware(task_handler: Callable[..., None]) -> Callable[[F], F]:
    """Decorator that routes CLI commands to task-specific handlers when in task context.

    Args:
        task_handler: Function to call when project_dir is a task directory.
                      Receives (project_dir, **kwargs) where kwargs are the
                      Click command parameters.

    Usage:
        @chunk.command("list")
        @click.option("--project-dir", ...)
        @task_aware(_list_task_chunks)
        def list_chunks(project_dir, **other_options):
            # This body runs only in single-repo mode
            ...
    """
```

Location: `src/cli/utils.py`

### Step 2: Write tests for the task_aware decorator

Before implementing, write tests in a new `tests/test_cli_utils.py` file:

1. **test_task_aware_routes_to_handler_in_task_dir**: When `project_dir` is a task directory, the task handler is called and the original function is NOT called
2. **test_task_aware_calls_original_in_normal_dir**: When `project_dir` is a normal directory, the original function is called and task handler is NOT called
3. **test_task_aware_passes_kwargs_to_handler**: The task handler receives all kwargs from the Click command
4. **test_task_aware_preserves_function_metadata**: The decorated function preserves `__name__`, `__doc__` etc.

These tests use mocking to isolate the decorator behavior from actual CLI commands.

Location: `tests/test_cli_utils.py`

### Step 3: Implement the task_aware decorator

Implement the decorator in `src/cli/utils.py` to make the tests pass:

```python
import functools
from typing import Callable, TypeVar
import pathlib

from task_utils import is_task_directory

F = TypeVar('F', bound=Callable[..., None])

# Chunk: docs/chunks/cli_task_context_dedup - Task-context routing decorator
def task_aware(task_handler: Callable[..., None]) -> Callable[[F], F]:
    """Decorator that routes CLI commands to task-specific handlers when in task context."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            project_dir = kwargs.get('project_dir', pathlib.Path('.'))
            if is_task_directory(project_dir):
                return task_handler(project_dir, **kwargs)
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator
```

### Step 4: Migrate chunk.py create command

Update `src/cli/chunk.py` `create` command:

**Before:**
```python
def create(short_names, project_dir, yes, future, ticket, projects):
    ...
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _start_task_chunks(project_dir, valid_names, ticket_id, status, projects)
        # If there were validation errors, exit with error code
        if validation_errors:
            raise SystemExit(1)
        return
```

**After:**
The create command has additional pre-processing before the task check (validation, name parsing). This is not a simple routing pattern - keep the manual check for this command.

**Decision:** Skip migration for `create` - the validation logic that runs before the task check makes it unsuitable for the decorator pattern.

### Step 5: Migrate chunk.py list command

Update `src/cli/chunk.py` `list_chunks` command:

**Before:**
```python
def list_chunks(..., project_dir):
    ...
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_chunks(current, last_active, recent, status_set, project_dir)
        return
```

**After:**
The status parsing and mutual exclusivity checks happen before the task check. Similar to create, this has pre-routing logic.

**Decision:** Skip migration for `list_chunks` - pre-routing validation makes it unsuitable.

### Step 6: Migrate chunk.py list-proposed command

**Before:**
```python
def list_proposed_chunks_cmd(project_dir):
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_proposed_chunks(project_dir)
        return
```

**After:** This is a pure routing pattern - can use decorator. However, the task handler has a different signature than what the decorator expects.

**Analysis:** The task handler takes only `project_dir`, but the decorator passes all kwargs. The handler needs to be adapted or the pattern adjusted.

### Step 7: Re-evaluate decorator design

After analyzing the actual usage patterns, we find:

1. **create commands**: Have validation/pre-processing before the task check
2. **list commands**: Often have status parsing/validation before the task check
3. **Simple commands**: Have clean routing but task handlers vary in signature

**Revised approach:** Instead of a decorator, create a helper function that encapsulates just the check-and-call pattern:

```python
def route_if_task_context(
    project_dir: pathlib.Path,
    task_handler: Callable[[pathlib.Path], T],
) -> T | None:
    """Route to task handler if in task context, otherwise return None.

    Usage:
        result = route_if_task_context(project_dir, lambda pd: _list_task_chunks(pd, ...))
        if result is not None:
            return
    """
    if is_task_directory(project_dir):
        return task_handler(project_dir)
    return None
```

**Problem:** This doesn't reduce boilerplate enough. The caller still needs the if-return pattern.

### Step 8: Final approach - Direct inline refactoring with helper

After careful analysis, the best approach is a helper that combines check + call + early return:

```python
def handle_task_context(
    project_dir: pathlib.Path,
    handler: Callable[[], None],
) -> bool:
    """Execute handler if in task context, return True if handled.

    Usage:
        if handle_task_context(project_dir, lambda: _list_task_chunks(project_dir, args)):
            return
    """
    if is_task_directory(project_dir):
        handler()
        return True
    return False
```

**Usage pattern:**
```python
def list_proposed_chunks_cmd(project_dir):
    if handle_task_context(project_dir, lambda: _list_task_proposed_chunks(project_dir)):
        return
    # Single-repo mode...
```

This reduces each call site from 3 lines to 2 lines and centralizes the `is_task_directory` import and check.

**Savings analysis:**
- Current: `if is_task_directory(project_dir):` + `_task_handler(...)` + `return` = 3 lines
- Proposed: `if handle_task_context(project_dir, lambda: ...):` + `return` = 2 lines
- For 10+ instances: ~10 lines saved, plus centralized import

**Verdict:** The savings are modest but the centralization is valuable for:
1. Consistent behavior if the check logic changes
2. Single import point for task awareness
3. Self-documenting pattern name

### Step 9: Implement handle_task_context helper

Add to `src/cli/utils.py`:

```python
# Chunk: docs/chunks/cli_task_context_dedup - Task-context routing helper
def handle_task_context(
    project_dir: pathlib.Path,
    handler: Callable[[], None],
) -> bool:
    """Execute handler if in task context, return True if handled.

    Use this helper to route CLI commands to task-specific handlers when running
    in a task directory (cross-repo mode). Returns True if the handler was called,
    allowing the caller to return early.

    Args:
        project_dir: The project directory to check.
        handler: Zero-argument callable to execute if in task context.
                 Typically a lambda capturing the task handler with arguments.

    Returns:
        True if handler was called (in task context), False otherwise.

    Usage:
        def list_proposed_chunks_cmd(project_dir):
            if handle_task_context(project_dir, lambda: _list_task_proposed_chunks(project_dir)):
                return
            # Single-repo mode continues here...
    """
    if is_task_directory(project_dir):
        handler()
        return True
    return False
```

Location: `src/cli/utils.py`

### Step 10: Write tests for handle_task_context

Add tests to `tests/test_cli_utils.py`:

1. **test_handle_task_context_calls_handler_in_task_dir**: When project_dir is a task directory, handler is called and True is returned
2. **test_handle_task_context_skips_handler_in_normal_dir**: When project_dir is normal, handler is NOT called and False is returned
3. **test_handle_task_context_handler_receives_no_args**: The handler is called with no arguments (it's a closure)

### Step 11: Migrate list-proposed command

Update `src/cli/chunk.py`:

```python
from cli.utils import handle_task_context, ...

def list_proposed_chunks_cmd(project_dir):
    """List all proposed chunks that haven't been created yet."""
    if handle_task_context(project_dir, lambda: _list_task_proposed_chunks(project_dir)):
        return
    # Single-repo mode...
```

### Step 12: Migrate external.py resolve command

Update `src/cli/external.py`:

```python
from cli.utils import handle_task_context

def resolve(..., project_dir):
    ...
    if handle_task_context(project_dir, lambda: _resolve_external_task_directory(
        project_dir, local_artifact_id, main_only, secondary_only, project
    )):
        return
    # Single repo mode...
```

### Step 13: Migrate narrative.py commands

Update `src/cli/narrative.py`:

**create_narrative:**
```python
if handle_task_context(project_dir, lambda: _start_task_narrative(project_dir, short_name, projects)):
    return
```

**list_narratives:**
```python
if handle_task_context(project_dir, lambda: _list_task_narratives_cmd(project_dir)):
    return
```

### Step 14: Migrate investigation.py commands

Update `src/cli/investigation.py`:

**create_investigation:**
```python
if handle_task_context(project_dir, lambda: _create_task_investigation(project_dir, short_name, projects)):
    return
```

**list_investigations:**
```python
if handle_task_context(project_dir, lambda: _list_task_investigations(project_dir)):
    return
```

### Step 15: Migrate subsystem.py commands

Update `src/cli/subsystem.py`:

**list_subsystems:**
```python
if handle_task_context(project_dir, lambda: _list_task_subsystems(project_dir)):
    return
```

**discover:**
```python
if handle_task_context(project_dir, lambda: _create_task_subsystem(project_dir, shortname, projects)):
    return
```

### Step 16: Migrate friction.py log command

Update `src/cli/friction.py`:

**log_entry:**
```python
if handle_task_context(project_dir, lambda: _log_entry_task_context(
    project_dir, title, description, impact, theme, theme_name, projects
)):
    return
```

### Step 17: Update imports across migrated files

Remove direct imports of `is_task_directory` from CLI modules that now use `handle_task_context`. The function is still imported in `cli/utils.py`.

Note: Some modules (chunk.py) may still need `is_task_directory` for non-routing uses (like `check_task_project_context`).

### Step 18: Run existing tests

Run the full test suite to verify behavioral equivalence:

```bash
uv run pytest tests/
```

All existing tests should pass without modification.

### Step 19: Update code_paths in GOAL.md

Add the files touched to the chunk's GOAL.md frontmatter:
- `src/cli/utils.py`
- `src/cli/chunk.py`
- `src/cli/narrative.py`
- `src/cli/investigation.py`
- `src/cli/subsystem.py`
- `src/cli/friction.py`
- `src/cli/external.py`
- `tests/test_cli_utils.py`

## Dependencies

None. This chunk uses only existing functionality (`is_task_directory` from `task_utils.py`) and standard library tools (`functools`, `pathlib`).

## Risks and Open Questions

1. **Lambda closure overhead**: Each call site uses a lambda to capture arguments. This adds minimal runtime overhead but makes stack traces slightly less readable. Acceptable for CLI commands where human-readable errors matter more than microsecond performance.

2. **Commands with pre-routing validation**: Some commands (like `chunk create`, `chunk list`) have validation logic that runs before the task context check. These cannot be trivially migrated. The plan handles this by documenting which commands are skipped.

3. **Reduced line savings vs. original goal**: The original goal estimated "30+ lines" of boilerplate reduction. The actual savings are closer to 10-15 lines due to the lambda syntax overhead. However, the centralization benefit (single check implementation) remains valuable.

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

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->