<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a simplification refactoring that removes dead code paths. The legacy `{NNNN}-{short_name}` directory format was a historical artifact from when artifacts had numeric sequence prefixes. The codebase now uses only `{short_name}` format for all artifact directories, and there is no usage of the legacy format in the wild.

The strategy is a systematic, file-by-file removal of:
1. Regex patterns matching `\d{4}-` prefixes
2. Conditional branches handling the legacy format
3. `extract_short_name()` calls that are now unnecessary (since directory name = short name)
4. Comments/docstrings referencing the dual format
5. Test fixtures and assertions for legacy format

The implementation follows a "core outward" approach:
- First simplify `src/models.py` (the foundation)
- Then update modules that import from models
- Finally update CLI commands and SPEC.md documentation

Per DEC-004 (Markdown references relative to project root), all path references remain project-root-relative.

## Subsystem Considerations

No subsystems are directly impacted by this removal. The `workflow_artifacts` subsystem pattern is preserved—only the internal implementation details for ID/pattern matching are simplified.

## Sequence

### Step 1: Simplify `src/models.py` core patterns

**Location**: `src/models.py`

1. **Simplify `extract_short_name()`** (lines 116-129):
   - Remove the `if re.match(r"^\d{4}-", dir_name)` branch
   - Make the function an identity function that returns `dir_name` unchanged
   - Update the docstring to remove references to legacy format

2. **Simplify `ARTIFACT_ID_PATTERN`** (line 135):
   - Remove the `\d{4}-.+` alternative
   - Change from `r"^(\d{4}-.+|[a-z][a-z0-9_-]*)$"` to `r"^[a-z][a-z0-9_-]*$"`
   - Update the comment to remove "Legacy pattern" reference

3. **Simplify `CHUNK_ID_PATTERN`** (line 138):
   - Same change as `ARTIFACT_ID_PATTERN`
   - Update the comment to remove "Legacy regex for backward compatibility" reference

4. **Simplify `ChunkRelationship.validate_chunk_id()`** (lines 153-172):
   - Remove the `if re.match(r"^\d{4}-", v)` branch that validates legacy format
   - Update error message to remove `{NNNN}-{short_name}` reference
   - Simplify docstring

5. **Simplify `SubsystemRelationship.validate_subsystem_id()`** (lines 187-206):
   - Same changes as `ChunkRelationship.validate_chunk_id()`

### Step 2: Simplify `src/subsystems.py`

**Location**: `src/subsystems.py`

1. **Simplify `SUBSYSTEM_DIR_PATTERN`** (line 29):
   - Remove the `\d{4}-.+` alternative
   - Change from `r"^(\d{4}-.+|[a-z][a-z0-9_-]*)$"` to `r"^[a-z][a-z0-9_-]*$"`
   - Update comment to remove "Legacy: {NNNN}-{short_name}" reference

2. **Simplify `is_subsystem_dir()`** (lines 127-142):
   - Remove the `if re.match(r"^\d{4}-", name)` branch (lines 139-141)
   - Return only `bool(SUBSYSTEM_DIR_PATTERN.match(name))`

3. **Simplify `find_by_shortname()`** (lines 145-160):
   - Remove the `extract_short_name(dirname)` call (line 157)
   - Compare directory names directly since `dirname == shortname`

4. **Simplify `find_duplicates()`** (lines 217-231):
   - Remove the `extract_short_name(name)` call (line 228)
   - Compare directory names directly

### Step 3: Simplify `src/chunks.py`

**Location**: `src/chunks.py`

1. **Simplify `find_duplicates()`** (lines 158-181):
   - Remove the `extract_short_name(name)` call (line 178)
   - Compare `name` directly with `target_short` since directory names are now the short name
   - Update docstring to remove legacy format handling mention

2. **Simplify `resolve_chunk_id()`** (lines 418-441):
   - Remove the legacy prefix match strategy (lines 433-435: `if name.startswith(f"{chunk_id}-")`)
   - Remove the `extract_short_name` import from the import list (line 52)
   - Update docstring to remove "Legacy prefix match" from supported strategies

### Step 4: Simplify `src/narratives.py`

**Location**: `src/narratives.py`

1. **Simplify `find_duplicates()`** (lines 220-234):
   - Remove the `extract_short_name(name)` call (line 231)
   - Compare `name` directly with `short_name`
   - Remove `extract_short_name` from the import list (line 16)

### Step 5: Simplify `src/investigations.py`

**Location**: `src/investigations.py`

1. **Simplify `find_duplicates()`** (lines 161-175):
   - Remove the `extract_short_name(name)` call (line 172)
   - Compare `name` directly with `short_name`
   - Remove `extract_short_name` from the import list (line 13)

### Step 6: Simplify `src/cluster_rename.py`

**Location**: `src/cluster_rename.py`

1. **Simplify `find_chunks_by_prefix()`** (lines 26-53):
   - Remove the `extract_short_name(chunk_name)` call (line 47)
   - Use `chunk_name` directly since directory names are now the short name
   - Update docstring to remove "Handles both legacy...and new...formats" (lines 33-34)

2. **Simplify `check_rename_collisions()`** (lines 57-98):
   - Remove the `extract_short_name(chunk_name)` call (line 79)
   - Remove the `if re.match(r"^\d{4}-", chunk_name)` sequence-number preservation logic (lines 84-88)
   - Use `new_short_name` directly as the new chunk name

3. **Simplify `_compute_new_chunk_name()`** (lines 137-155):
   - Remove the `extract_short_name(chunk_name)` call (line 148)
   - Remove the `if re.match(r"^\d{4}-", chunk_name)` sequence-number preservation logic (lines 151-154)
   - Return `new_short_name` directly

4. **Simplify reference-finding functions**:
   - `find_created_after_references()` (line 187): Remove `extract_short_name(ref)` call
   - `find_subsystem_chunk_references()` (line 229): Remove `extract_short_name(chunk_id)` call
   - `find_narrative_chunk_references()` (line 271): Remove `extract_short_name(proposed.chunk_directory)` call
   - `find_investigation_chunk_references()` (line 315): Remove `extract_short_name(proposed.chunk_directory)` call

5. **Remove the `extract_short_name` import** (line 22)

### Step 7: Simplify CLI commands

**Location**: `src/cli/chunk.py`

1. **Simplify `status` command** (lines 1043-1091):
   - Remove the `from models import extract_short_name` import (line 1045)
   - Remove the `shortname = extract_short_name(resolved_id)` call (line 1060)
   - Use `resolved_id` directly since directory names are now the short name

**Location**: `src/cli/investigation.py`

1. **Simplify `status` command** (lines 234-278):
   - Remove the `from models import extract_short_name` import (line 240)
   - Remove the `shortname = extract_short_name(investigation_id)` call (line 248)
   - Use `investigation_id` directly

### Step 8: Update `docs/trunk/SPEC.md`

**Location**: `docs/trunk/SPEC.md`

1. **Update Directory Structure diagram** (lines 115-142):
   - Change `{NNNN}-{short_name}[-{ticket}]/` to `{short_name}/` for chunks
   - Change `{NNNN}-{short_name}/` to `{short_name}/` for subsystems and investigations

2. **Update Identifiers and Metadata section** (lines 102-109):
   - Remove or simplify "Chunk ID" definition (line 104) since it's no longer a 4-digit number
   - Update to reflect that chunk directories use `{short_name}` format

3. **Update Chunk Directory Naming section** (lines 189-197):
   - Remove `{chunk_id}` from the format
   - Remove "chunk_id: 4-digit zero-padded integer" explanation
   - Update examples to use new format

4. **Update Subsystem Directory Naming section** (lines 256-262):
   - Change format from `{subsystem_id}-{short_name}` to `{short_name}`
   - Remove "subsystem_id: 4-digit zero-padded integer" explanation
   - Update examples

5. **Update Investigation Directory Naming section** (lines 334-340):
   - Change format from `{investigation_id}-{short_name}` to `{short_name}`
   - Remove "investigation_id: 4-digit zero-padded integer" explanation
   - Update examples

6. **Update CLI command descriptions** (lines 448-476 for `ve chunk start`):
   - Update postconditions to show new directory format

### Step 9: Update tests

**Location**: `tests/`

Update tests in files that use legacy `{NNNN}-` format directories. Key files to update:

1. **`tests/test_models.py`**:
   - Remove tests for legacy format handling in `extract_short_name()`
   - Update `ARTIFACT_ID_PATTERN` and `CHUNK_ID_PATTERN` tests to only test new format
   - Remove legacy format validation tests for `ChunkRelationship` and `SubsystemRelationship`

2. **`tests/test_chunks.py`**:
   - Update directory fixtures to use `{short_name}` format
   - Remove tests for legacy prefix matching in `resolve_chunk_id()`
   - Update `find_duplicates()` tests

3. **`tests/test_subsystems.py`**:
   - Update directory fixtures to use `{short_name}` format
   - Remove tests for legacy format in `is_subsystem_dir()`
   - Update `find_by_shortname()` and `find_duplicates()` tests

4. **`tests/test_cluster_rename.py`**:
   - Update test fixtures to use new format
   - Remove tests for legacy sequence-number preservation

5. **`tests/test_narratives.py`** and **`tests/test_investigations.py`**:
   - Update directory fixtures
   - Update `find_duplicates()` tests

6. **Other affected test files** (identified via grep):
   - `test_artifact_ordering.py`, `test_chunk_list_proposed.py`, `test_chunk_validate.py`
   - `test_cluster_list.py`, `test_external_resolve.py`, `test_external_resolve_cli.py`
   - `test_friction.py`, `test_friction_workflow.py`, `test_integrity.py`
   - `test_investigation_template.py`, `test_narratives.py`, `test_orchestrator_*.py`
   - `test_repo_cache.py`, `test_subsystem_*.py`, `test_task_*.py`, `test_template_system.py`

For each test file, update any test fixtures that create directories with `{NNNN}-` prefix format.

### Step 10: Verify and clean up

1. **Run tests**: `uv run pytest tests/` to ensure all tests pass

2. **Search for remaining patterns**:
   - `grep -r "\\d{4}-" src/` to verify no legacy patterns remain
   - `grep -r "NNNN" src/` to verify no comments reference legacy format

3. **Remove any remaining `extract_short_name` usage** that is now just an identity function:
   - If `extract_short_name()` is still imported but never called, remove the import
   - If it's only used in a trivial way, simplify those call sites

## Dependencies

None. This chunk has no dependencies on other chunks. Per the narrative's `depends_on: []`, this is an independent simplification that can proceed immediately.

## Risks and Open Questions

1. **Test discovery completeness**: The grep for `\d{4}-` found 28 test files. Some may use legacy format in ways not immediately visible (string concatenation, fixtures from helper functions). Mitigation: Run tests after each major step to catch failures early.

2. **External callers**: If any external code or agent commands directly parse directory names expecting `{NNNN}-` format, they will break. Mitigation: The goal states "no usage of the legacy format in the wild" has been confirmed, so this risk is low.

3. **`extract_short_name()` identity transformation**: After simplification, `extract_short_name()` becomes `return dir_name`. This is intentional—keeping the function allows downstream chunk `models_subpackage` to work with a clean interface. Alternatively, the function could be removed entirely, but that would require more invasive changes to callers.

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