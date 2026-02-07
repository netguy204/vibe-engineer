<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This decomposition follows the established pattern from `src/models/` (decomposed in `models_subpackage` chunk) and `src/cli/` (decomposed in `cli_formatters_extract` chunk): create a package with cohesive modules and a re-exporting `__init__.py` to maintain backward compatibility.

The strategy:

1. **Create `src/task/` package** with focused modules organized by responsibility, not by artifact type. The goal is to eliminate the duplicated artifact-type-specific functions (`create_task_chunk`, `create_task_narrative`, etc.) in favor of generic operations parameterized by `ArtifactType`.

2. **Establish exception hierarchy** with a common `TaskError` base class in `src/task/exceptions.py`. All task-related exceptions (`TaskChunkError`, `TaskPromoteError`, etc.) will inherit from it, enabling consistent error handling.

3. **Consolidate duplicated patterns** into generic implementations:
   - `create_task_artifact()` replaces the four `create_task_*` functions
   - `list_task_artifacts()` replaces the four `list_task_*` functions
   - `add_dependents_to_artifact()` already exists and is generic; the type-specific wrappers can be removed

4. **Maintain backward compatibility** via `src/task/__init__.py` re-exports. Existing `from task_utils import ...` statements will continue to work.

5. **Preserve all existing tests** by maintaining the same public API. Test files import from `task_utils` which will re-export from `src/task/`.

The decomposition follows the principle that module boundaries should reflect cohesive responsibilities, not just code volume. Each module owns one concern end-to-end.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk IMPLEMENTS the refactoring of `src/task_utils.py`, which is a primary implementation location for this subsystem. The subsystem's code_references section lists many functions in task_utils.py that will move to the new package structure. After this chunk completes, the subsystem documentation should be updated to reflect the new module locations (e.g., `src/task/config.py#load_task_config` instead of `src/task_utils.py#load_task_config`).

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow artifact patterns (Chunks, Narratives, Investigations, Subsystems managers) from this subsystem. The generic artifact operations will leverage `ArtifactType` and the manager pattern.

## Sequence

### Step 1: Create package structure and exceptions module

Create the `src/task/` package directory with `__init__.py` and `exceptions.py`.

**Location**: `src/task/__init__.py`, `src/task/exceptions.py`

**Actions**:
1. Create `src/task/` directory
2. Create `src/task/exceptions.py` with:
   - `TaskError` base exception class
   - All specific exception classes inheriting from it:
     - `TaskChunkError`
     - `TaskNarrativeError`
     - `TaskInvestigationError`
     - `TaskSubsystemError`
     - `TaskPromoteError`
     - `TaskArtifactListError`
     - `TaskCopyExternalError`
     - `TaskRemoveExternalError`
     - `TaskFrictionError`
     - `TaskOverlapError`
     - `TaskActivateError`
3. Create empty `src/task/__init__.py` (will populate later)

**Success criteria**: Package structure exists, all exceptions defined with proper inheritance.

### Step 2: Create config module

Extract config loading, project resolution, and directory detection functions.

**Location**: `src/task/config.py`

**Functions to move** (~230 lines):
- `parse_projects_option()` - Parse --projects CLI option
- `resolve_project_ref()` - Resolve flexible project reference to org/repo
- `resolve_project_qualified_ref()` - Parse project-qualified code references
- `is_task_directory()` - Detect .ve-task.yaml presence
- `resolve_repo_directory()` - Resolve org/repo to filesystem path
- `load_task_config()` - Load and validate TaskConfig

**Helper functions** (task directory related):
- `find_task_directory()` - Walk up to find task directory
- `TaskProjectContext` dataclass
- `check_task_project_context()` - Check if in project within task

**Success criteria**: All config-related functions work from new location.

### Step 3: Create artifact_ops module with generic operations

Create generic CRUD operations for task artifacts, replacing duplicated implementations.

**Location**: `src/task/artifact_ops.py`

**New generic functions** to implement:
- `create_task_artifact(task_dir, artifact_type, short_name, ...)` - Generic creation
- `list_task_artifacts(task_dir, artifact_type)` - Generic listing
- `add_dependents_to_artifact()` - Already exists, move here
- `append_dependent_to_artifact()` - Already exists, move here
- `list_task_artifacts_grouped()` - Already exists, move here
- `list_task_proposed_chunks()` - Already exists, move here

**Convenience wrappers** (for backward compatibility, can be thin):
- `create_task_chunk()` → calls `create_task_artifact(ArtifactType.CHUNK, ...)`
- `create_task_narrative()` → calls `create_task_artifact(ArtifactType.NARRATIVE, ...)`
- `create_task_investigation()` → calls `create_task_artifact(ArtifactType.INVESTIGATION, ...)`
- `create_task_subsystem()` → calls `create_task_artifact(ArtifactType.SUBSYSTEM, ...)`
- `list_task_chunks()` → calls `list_task_artifacts(ArtifactType.CHUNK)`
- `list_task_narratives()` → calls `list_task_artifacts(ArtifactType.NARRATIVE)`
- `list_task_investigations()` → calls `list_task_artifacts(ArtifactType.INVESTIGATION)`
- `list_task_subsystems()` → calls `list_task_artifacts(ArtifactType.SUBSYSTEM)`

**Type-specific add_dependents wrappers** (thin, for backward compatibility):
- `add_dependents_to_chunk()` → calls `add_dependents_to_artifact(ArtifactType.CHUNK, ...)`
- `add_dependents_to_narrative()` → calls `add_dependents_to_artifact(ArtifactType.NARRATIVE, ...)`
- `add_dependents_to_investigation()` → calls `add_dependents_to_artifact(ArtifactType.INVESTIGATION, ...)`
- `add_dependents_to_subsystem()` → calls `add_dependents_to_artifact(ArtifactType.SUBSYSTEM, ...)`

**Other functions to move here**:
- `get_current_task_chunk()` - Get IMPLEMENTING chunk from external repo
- `get_next_chunk_id()` (deprecated but still used)
- `is_external_chunk()` - Convenience wrapper
- `activate_task_chunk()` - Activate FUTURE chunk
- `_list_local_artifacts()` - Helper for grouped listing

**Success criteria**: Generic implementation reduces code duplication from ~800 lines to ~400 lines. All type-specific functions remain available as thin wrappers.

### Step 4: Create promote module

Extract artifact promotion logic.

**Location**: `src/task/promote.py`

**Functions to move** (~430 lines):
- `identify_source_project()` - Determine which project contains artifact
- `_get_artifact_created_after()` - Parse created_after from main file
- `promote_artifact()` - Core promotion logic

**Success criteria**: Promotion functionality works from new location.

### Step 5: Create external module

Extract external artifact copy/remove operations.

**Location**: `src/task/external.py`

**Functions to move** (~340 lines):
- `copy_artifact_as_external()` - Copy artifact as external reference
- `remove_artifact_from_external()` - Remove external reference
- `remove_dependent_from_artifact()` - Remove dependent entry from frontmatter

**Success criteria**: External copy/remove operations work from new location.

### Step 6: Create friction module

Extract friction entry operations.

**Location**: `src/task/friction.py`

**Functions to move** (~200 lines):
- `create_task_friction_entry()` - Create friction entry in task context
- `add_external_friction_source()` - Add external friction source to project

**Success criteria**: Friction operations work from new location.

### Step 7: Create overlap module

Extract overlap detection logic.

**Location**: `src/task/overlap.py`

**Functions to move** (~240 lines):
- `TaskOverlapResult` dataclass
- `find_task_overlapping_chunks()` - Find overlapping chunks across repos
- `_compute_cross_project_overlap()` - Helper for cross-project comparison
- `normalize_ref()` (nested function, can be module-level)

**Success criteria**: Overlap detection works from new location.

### Step 8: Wire up __init__.py re-exports

Populate `src/task/__init__.py` with all public names for backward compatibility.

**Location**: `src/task/__init__.py`

**Actions**:
1. Import all public names from submodules
2. Re-export via `__all__`
3. Ensure existing `from task_utils import X` patterns work

**Success criteria**: `from task_utils import X` works for all public names.

### Step 9: Update task_utils.py as re-export shim

Replace the monolithic `src/task_utils.py` with a thin re-export layer.

**Location**: `src/task_utils.py`

**Actions**:
1. Remove all function/class definitions
2. Import and re-export everything from `src/task/`
3. Keep module docstring and backreference comments (updated)

**Success criteria**: All existing imports from `task_utils` continue to work.

### Step 10: Verify tests pass

Run the full test suite to verify no regressions.

**Location**: `tests/`

**Actions**:
1. Run `uv run pytest tests/`
2. Fix any import path issues in tests
3. Verify all 2,516+ tests pass

**Success criteria**: All tests pass without modification (except possibly import-path updates if tests import internal helpers directly).

### Step 11: Update subsystem documentation

Update `docs/subsystems/cross_repo_operations/OVERVIEW.md` code_references to reflect new module locations.

**Location**: `docs/subsystems/cross_repo_operations/OVERVIEW.md`

**Actions**:
1. Update code_references paths from `src/task_utils.py#X` to `src/task/module.py#X`
2. Update Implementation Locations section

**Success criteria**: Subsystem documentation reflects new code structure.

---

**BACKREFERENCE COMMENTS**

When implementing the new modules, add backreference comments:

```python
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition
```

Each module should have a module-level backreference. Function-level backreferences from the original task_utils.py should be preserved in the new locations.

## Dependencies

This chunk depends on the chunks listed in `created_after`:
- `orch_prune_consolidate`
- `chunk_validator_extract`
- `cli_formatters_extract`
- `frontmatter_import_consolidate`
- `models_subpackage`
- `orch_client_context`
- `project_artifact_registry`
- `remove_legacy_prefix`
- `scheduler_decompose`

These chunks established the patterns this decomposition follows (package structure, re-exports, etc.) and made changes to code this chunk touches.

## Risks and Open Questions

1. **Circular import risk**: The `task/` modules will need to import from various other modules (chunks.py, narratives.py, etc.) which may import from task_utils. Need to carefully check import order and possibly use lazy imports.

2. **Manager class lookup by artifact type**: The generic `create_task_artifact()` needs to instantiate the correct manager class (Chunks, Narratives, etc.) based on `ArtifactType`. May need a registry pattern or match statement.

3. **Test import modifications**: While the plan aims for no test changes, some test files may import internal helpers that move. These would need path updates.

4. **Generic vs type-specific parameters**: `create_task_chunk()` has chunk-specific parameters (`ticket_id`, `status`) that don't apply to other artifact types. The generic function will need to handle these via `**kwargs` or type-specific branches.

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