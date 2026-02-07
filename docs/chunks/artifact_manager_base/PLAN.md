<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extracts a shared `ArtifactManager` base class and a reusable `StateMachine` class to eliminate duplicated lifecycle management code across the four artifact types (Chunks, Narratives, Investigations, Subsystems).

**Strategy:**

1. **Create a `StateMachine` class** that encapsulates transition validation logic. Currently, each manager duplicates the same pattern:
   ```python
   valid_transitions = VALID_*_TRANSITIONS.get(current_status, set())
   if new_status not in valid_transitions:
       # Build error message...
   ```
   The `StateMachine` will accept a transition map and provide a `validate_transition()` method with standardized error messages.

2. **Create an abstract `ArtifactManager` base class** that captures the shared pattern:
   - `__init__(project_dir)` storing project_dir and computing artifact directory
   - `enumerate_artifacts()` listing artifact directories
   - `get_status(artifact_id)` parsing frontmatter and extracting status
   - `update_status(artifact_id, new_status)` using StateMachine for validation
   - `_update_frontmatter(artifact_id, field, value)` using frontmatter.py utilities

3. **Refactor each manager** to subclass `ArtifactManager`:
   - Implement abstract properties: `artifact_dir_name`, `main_filename`, `frontmatter_model_class`, `status_enum`, `transition_map`
   - Remove duplicated `get_status`, `update_status`, and `_update_*_frontmatter` methods
   - Retain artifact-specific methods (e.g., `Chunks.validate_subsystem_refs`, `Subsystems.find_overlapping_subsystems`)

4. **Test-first approach**: Write failing tests for the StateMachine and ArtifactManager classes first, then implement to make them pass. Verify existing tests continue to pass after refactoring.

**Building on:**
- `src/frontmatter.py` - Already provides `parse_frontmatter`, `update_frontmatter_field` utilities
- `src/models.py` - Contains status enums and transition maps
- docs/subsystems/workflow_artifacts - Canonical pattern documentation

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk **IMPLEMENTS** a key piece of the workflow artifact pattern - the base class that enforces the manager class interface described in Hard Invariant #6. The subsystem documents that every workflow type needs `enumerate_`, `create_`, `parse_frontmatter` methods; this chunk formalizes that in code via an abstract base class.

## Sequence

### Step 1: Create StateMachine class with tests

Create `src/state_machine.py` with a `StateMachine` class that:
- Accepts a transition map (`dict[StatusEnum, set[StatusEnum]]`) and the status enum type
- Provides `validate_transition(current: StatusEnum, new: StatusEnum) -> None` that raises `ValueError` with descriptive messages
- Error messages include: valid transitions list (for non-terminal states) or "terminal state" indicator

Write tests first in `tests/test_state_machine.py`:
- Test valid transition passes without exception
- Test invalid transition raises ValueError with correct message
- Test terminal state transition raises ValueError mentioning "terminal"
- Test with all four status enum types (ChunkStatus, NarrativeStatus, InvestigationStatus, SubsystemStatus)

Location: `src/state_machine.py`, `tests/test_state_machine.py`

### Step 2: Create ArtifactManager abstract base class with tests

Create `src/artifact_manager.py` with an abstract `ArtifactManager` class:

**Abstract properties (must be overridden):**
- `artifact_dir_name: str` - e.g., "chunks", "narratives"
- `main_filename: str` - e.g., "GOAL.md", "OVERVIEW.md"
- `frontmatter_model_class: type[BaseModel]` - Pydantic model class
- `status_enum: type[StrEnum]` - Status enum class
- `transition_map: dict` - Valid transitions dict

**Concrete methods:**
- `__init__(project_dir: Path)` - stores project_dir, computes artifact_dir path
- `artifact_dir: Path` (property) - returns `project_dir / "docs" / artifact_dir_name`
- `enumerate_artifacts() -> list[str]` - lists subdirectories
- `get_artifact_path(artifact_id: str) -> Path` - returns artifact directory path
- `get_main_file_path(artifact_id: str) -> Path` - returns path to main markdown file
- `parse_frontmatter(artifact_id: str)` - parses frontmatter using frontmatter.py
- `get_status(artifact_id: str)` - returns status from parsed frontmatter
- `update_status(artifact_id: str, new_status)` - validates and updates status
- `_update_frontmatter(artifact_id: str, field: str, value: Any)` - updates a field

Write tests first in `tests/test_artifact_manager.py`:
- Create a minimal concrete subclass for testing (e.g., `TestManager`)
- Test `enumerate_artifacts()` finds directories
- Test `get_status()` returns correct status
- Test `update_status()` with valid transition succeeds
- Test `update_status()` with invalid transition raises ValueError
- Test `_update_frontmatter()` updates field correctly

Location: `src/artifact_manager.py`, `tests/test_artifact_manager.py`

### Step 3: Refactor Subsystems to use ArtifactManager

Refactor `src/subsystems.py`:
- Import `ArtifactManager` and `StateMachine`
- Make `Subsystems` inherit from `ArtifactManager`
- Implement required abstract properties:
  - `artifact_dir_name = "subsystems"`
  - `main_filename = "OVERVIEW.md"`
  - `frontmatter_model_class = SubsystemFrontmatter`
  - `status_enum = SubsystemStatus`
  - `transition_map = VALID_STATUS_TRANSITIONS`
- Remove duplicated `get_status()`, `update_status()`, `_update_overview_frontmatter()` methods
- Keep `subsystems_dir` as an alias property for backward compatibility: `return self.artifact_dir`
- Keep `enumerate_subsystems()` as an alias: `return self.enumerate_artifacts()`
- Keep all artifact-specific methods: `is_subsystem_dir()`, `find_by_shortname()`, `create_subsystem()`, `parse_subsystem_frontmatter()`, `find_duplicates()`, `validate_chunk_refs()`, `find_overlapping_subsystems()`, `_find_overlapping_refs()`

Run existing tests: `pytest tests/test_subsystems.py tests/test_subsystem_*.py`

Location: `src/subsystems.py`

### Step 4: Refactor Investigations to use ArtifactManager

Refactor `src/investigations.py`:
- Make `Investigations` inherit from `ArtifactManager`
- Implement required abstract properties:
  - `artifact_dir_name = "investigations"`
  - `main_filename = "OVERVIEW.md"`
  - `frontmatter_model_class = InvestigationFrontmatter`
  - `status_enum = InvestigationStatus`
  - `transition_map = VALID_INVESTIGATION_TRANSITIONS`
- Remove duplicated `get_status()`, `update_status()`, `_update_overview_frontmatter()` methods
- Keep `investigations_dir` as alias property for backward compatibility
- Keep `enumerate_investigations()` as alias method
- Keep artifact-specific methods: `create_investigation()`, `find_duplicates()`, `parse_investigation_frontmatter()`

Run existing tests: `pytest tests/test_investigations.py tests/test_investigation_*.py`

Location: `src/investigations.py`

### Step 5: Refactor Narratives to use ArtifactManager

Refactor `src/narratives.py`:
- Make `Narratives` inherit from `ArtifactManager`
- Implement required abstract properties:
  - `artifact_dir_name = "narratives"`
  - `main_filename = "OVERVIEW.md"`
  - `frontmatter_model_class = NarrativeFrontmatter`
  - `status_enum = NarrativeStatus`
  - `transition_map = VALID_NARRATIVE_TRANSITIONS`
- Remove duplicated `get_status()`, `update_status()`, `_update_overview_frontmatter()` methods
- Keep `narratives_dir` as alias property for backward compatibility
- Keep `enumerate_narratives()` as alias method
- Keep artifact-specific methods: `create_narrative()`, `find_duplicates()`, `parse_narrative_frontmatter()`
- Note: Narratives has special handling for legacy 'chunks' field mapping to 'proposed_chunks' - keep that logic in `parse_narrative_frontmatter()`

Run existing tests: `pytest tests/test_narratives.py tests/test_narrative_*.py`

Location: `src/narratives.py`

### Step 6: Refactor Chunks to use ArtifactManager

Refactor `src/chunks.py`:
- Make `Chunks` inherit from `ArtifactManager`
- Implement required abstract properties:
  - `artifact_dir_name = "chunks"`
  - `main_filename = "GOAL.md"`
  - `frontmatter_model_class = ChunkFrontmatter`
  - `status_enum = ChunkStatus`
  - `transition_map = VALID_CHUNK_TRANSITIONS`
- Remove duplicated `get_status()`, `update_status()` methods (already using task_utils.update_frontmatter_field)
- Keep `chunk_dir` as alias property for backward compatibility
- Keep `enumerate_chunks()` as alias method
- Keep ALL artifact-specific methods - Chunks has the most: `find_duplicates()`, `list_chunks()`, `get_latest_chunk()`, `get_current_chunk()`, `get_recent_active_chunks()`, `get_last_active_chunk()`, `activate_chunk()`, `create_chunk()`, `resolve_chunk_id()`, `get_chunk_goal_path()`, `get_success_criteria()`, `parse_chunk_frontmatter()`, `parse_chunk_frontmatter_with_errors()`, `_parse_frontmatter_from_content()`, `resolve_chunk_location()`, `parse_code_references()`, `find_overlapping_chunks()`, `validate_chunk_complete()`, validation methods, etc.

Run existing tests: `pytest tests/test_chunks.py tests/test_chunk_*.py`

Location: `src/chunks.py`

### Step 7: Run full test suite and add code backreferences

Run the complete test suite to verify no regressions:
```bash
pytest tests/
```

Add backreference comments to the new files:
- `src/state_machine.py`: Add module-level chunk backreference
- `src/artifact_manager.py`: Add module-level chunk and subsystem backreferences
- Each refactored manager: Add class-level chunk backreference

Update `code_paths` in `docs/chunks/artifact_manager_base/GOAL.md` to list all touched files.

## Dependencies

- **frontmatter_io chunk**: This chunk depends on `frontmatter_io` being complete. The GOAL.md frontmatter shows `depends_on: [frontmatter_io]`. The `frontmatter.py` module with `parse_frontmatter`, `update_frontmatter_field`, etc. must be in place. Based on code review, this is already complete.

## Risks and Open Questions

1. **Backward compatibility of alias properties**: The refactored managers need to keep `chunk_dir`, `narratives_dir`, `investigations_dir`, `subsystems_dir` as alias properties since existing code may reference them. Need to verify all call sites.

2. **Chunks has unique patterns**: The Chunks class has many more methods than the other managers. The base class extraction should focus on the shared lifecycle methods (get_status, update_status, _update_frontmatter) without trying to generalize chunk-specific features like `resolve_chunk_id` or `validate_chunk_complete`.

3. **Different frontmatter parsing patterns**: Narratives has special handling for the legacy 'chunks' → 'proposed_chunks' field mapping. This artifact-specific logic should remain in `parse_narrative_frontmatter()` rather than being pushed into the base class.

4. **Import cycles**: Need to be careful about import structure. `state_machine.py` and `artifact_manager.py` should not import from the concrete managers. They can import from `models.py` and `frontmatter.py`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->