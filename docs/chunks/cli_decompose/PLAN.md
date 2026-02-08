# Implementation Plan

## Approach

Decompose the three largest CLI files by applying the existing patterns in this codebase:

1. **Extract pure domain logic to the domain layer** - The `_parse_status_filters` function in `chunk.py` has no Click dependency and is pure parsing logic. Move it to `src/models/chunk.py` alongside `ChunkStatus`, making it testable without CLI machinery.

2. **Extract shared formatters to `cli/formatters.py`** - The list rendering logic in `chunk.py` (lines ~497-580) uses deeply nested if/elif chains. Extract a `format_chunk_list_item` helper to `cli/formatters.py`, matching the existing `artifact_to_json_dict` pattern.

3. **Use `handle_task_context` consistently** - The `create` and `list` commands in `chunk.py` have manual task-context detection. Migrate to `handle_task_context` from `cli/utils.py`, matching all other CLI modules.

4. **Extract streaming logic to the orchestrator package** - The `orch_tail` command (lines ~727-877) contains log streaming/polling logic that belongs in the orchestrator package for independent testability. Create `src/orchestrator/log_streaming.py`.

5. **Consolidate duplicated prompting** - The friction log has `log_entry` and `_log_entry_task_context` with ~100 lines of near-identical prompting code. Extract a shared `prompt_friction_entry` helper.

Following TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write tests for the new domain-layer function (`parse_status_filters`) and the streaming logic extraction before implementation. The formatter extraction is primarily refactoring, tested by existing CLI tests passing.

## Subsystem Considerations

- **docs/subsystems/orchestrator**: This chunk USES the orchestrator subsystem by extracting log streaming logic into a new module within the orchestrator package. The extraction follows the existing modular pattern (e.g., `log_parser.py`, `dependencies.py`).

- **docs/subsystems/workflow_artifacts**: This chunk USES ChunkStatus from the workflow artifacts subsystem by moving status parsing to the domain layer.

## Sequence

### Step 1: Write test for `parse_status_filters`

Create test cases in `tests/test_models_chunk.py` (or a new file if none exists) for the domain-layer `parse_status_filters` function:
- Valid status string parsing (case-insensitive)
- Invalid status detection with error message
- Multiple statuses via comma separation
- Combination of convenience flags and --status option
- Empty input returns None

Location: `tests/test_models_chunk.py`

### Step 2: Extract `_parse_status_filters` to domain layer

Move `_parse_status_filters` from `src/cli/chunk.py` to `src/models/chunk.py` as `parse_status_filters` (dropping the underscore since it's now public API).

The function becomes:
```python
def parse_status_filters(
    status_strings: tuple[str, ...],
    future_flag: bool = False,
    active_flag: bool = False,
    implementing_flag: bool = False,
) -> tuple[set[ChunkStatus] | None, str | None]:
```

Update `src/cli/chunk.py` to import from `models` and call the new function.

Location: `src/models/chunk.py`, `src/cli/chunk.py`

### Step 3: Extract chunk list formatting to `formatters.py`

Create `format_chunk_list_entry` in `src/cli/formatters.py`:

```python
def format_chunk_list_entry(
    chunk_name: str,
    status: str,
    is_tip: bool,
    error: str | None = None,
    external_ref: ExternalArtifactRef | None = None,
) -> str:
    """Format a single chunk list entry for text output."""
```

Replace the deeply nested if/elif chains in `list_chunks` (lines ~501-569) with calls to this formatter.

Location: `src/cli/formatters.py`, `src/cli/chunk.py`

### Step 4: Migrate `chunk create` to use `handle_task_context`

The `create` command manually checks `is_task_directory`. Refactor to:

```python
def create(short_names, project_dir, yes, future, ticket, projects):
    if handle_task_context(project_dir, lambda: _start_task_chunks(...)):
        if validation_errors:
            raise SystemExit(1)
        return
    # Single-repo mode continues...
```

This matches the pattern used in `list-proposed` and other commands.

Location: `src/cli/chunk.py`

### Step 5: Migrate `chunk list` to use `handle_task_context`

Similar to Step 4, refactor the `list_chunks` command to use `handle_task_context` for task-context routing.

Location: `src/cli/chunk.py`

### Step 6: Write test for log streaming extraction

Create test cases in `tests/test_orchestrator_log_streaming.py`:
- `get_phase_log_files` returns existing files in phase order
- `stream_phase_logs` (the core streaming logic) handles file position tracking
- Handles missing log directory gracefully

Location: `tests/test_orchestrator_log_streaming.py`

### Step 7: Extract `orch_tail` streaming logic to orchestrator package

Create `src/orchestrator/log_streaming.py` with:

```python
def get_phase_log_files(log_dir: Path) -> list[tuple[WorkUnitPhase, Path]]:
    """Get list of existing phase log files in order."""

def stream_phase_log(
    log_file: Path,
    phase: WorkUnitPhase,
    start_position: int = 0,
) -> Iterator[tuple[str, int]]:
    """Stream lines from a phase log file, yielding (line, new_position)."""

def display_phase_log(
    phase: WorkUnitPhase,
    log_file: Path,
    show_header: bool = True,
    output: Callable[[str], None] = print,
):
    """Display a complete phase log file."""
```

Refactor `orch_tail` in `src/cli/orch.py` to use these functions, reducing it to CLI wiring only.

Location: `src/orchestrator/log_streaming.py`, `src/cli/orch.py`

### Step 8: Extract shared friction prompting logic

Create `_prompt_friction_inputs` in `src/cli/friction.py`:

```python
def _prompt_friction_inputs(
    title: str | None,
    description: str | None,
    impact: str | None,
    theme: str | None,
    theme_name: str | None,
    existing_themes: set[str],
    show_themes: bool = True,
) -> tuple[str, str, str, str, str | None]:
    """Prompt for missing friction entry inputs.

    Returns (title, description, impact, theme_id, theme_name).
    Raises SystemExit on validation errors or when non-interactive.
    """
```

Refactor both `log_entry` and `_log_entry_task_context` to call this helper, eliminating the duplicated prompting code.

Location: `src/cli/friction.py`

### Step 9: Verify line count reduction and run tests

Run `wc -l` on modified files to verify:
- `src/cli/chunk.py` is under 800 lines
- `src/cli/orch.py` is under 800 lines

Run full test suite to ensure no behavioral changes:
```bash
uv run pytest tests/
```

Location: N/A (verification)

### Step 10: Update code_paths in GOAL.md

Update the chunk's frontmatter with the files actually touched.

Location: `docs/chunks/cli_decompose/GOAL.md`

## Dependencies

This chunk depends on these completed chunks (per `created_after` in GOAL.md):
- `model_package_cleanup` - Models are organized into subpackages
- `orchestrator_api_decompose` - Orchestrator package structure exists
- `task_operations_decompose` - Task utilities are extracted

No external library dependencies.

## Risks and Open Questions

- **Test coverage for streaming logic**: The follow-mode streaming in `orch_tail` uses file polling which is hard to test deterministically. Will use mock filesystem or short timeout to make tests reliable.

- **Backward compatibility**: The `parse_status_filters` move to the domain layer changes import paths. Internal-only usage means no public API break, but verify no external callers.

- **Line count target**: The 800-line target is approximate. If refactoring yields 820 lines with clean structure, that's acceptable. The goal is improved separation of concerns, not a hard metric.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->