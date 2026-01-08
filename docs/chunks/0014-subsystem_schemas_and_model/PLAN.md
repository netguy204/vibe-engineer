# Implementation Plan

## Approach

This chunk establishes the data model for subsystem documentation. We follow test-driven development per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first, then implement the minimum code to make them pass.

**Strategy:**
1. Define Pydantic models in `src/models.py` following the existing patterns (enum, BaseModel, field_validator)
2. Create a new `src/subsystems.py` module following the `Chunks` and `Narratives` class patterns
3. Write tests that verify the models validate correctly and the utility class methods work

**Existing code to build on:**
- `src/models.py` - Contains `SymbolicReference` which we'll reuse for `code_references`
- `src/chunks.py` - `Chunks` class provides the pattern for `Subsystems` class (project_dir, dir property, enumerate, parse frontmatter)
- `src/narratives.py` - `Narratives` class provides a simpler pattern also worth referencing
- `tests/test_models.py` - Shows how to test Pydantic validation
- `tests/test_narratives.py` - Shows how to test the utility class pattern

**Reference:** DEC-004 requires all file references in markdown to be relative to project root, which is consistent with how we'll reference subsystem directories.

## Sequence

### Step 1: Write tests for SubsystemStatus enum

Create `tests/test_subsystems.py` with tests for the SubsystemStatus enum:
- Verify all five status values exist: DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED
- Verify the enum is a string enum for YAML serialization compatibility

Location: tests/test_subsystems.py

### Step 2: Implement SubsystemStatus enum

Add the SubsystemStatus enum to `src/models.py`:
- Use `StrEnum` for YAML compatibility (string values in frontmatter)
- Define the five status values

Location: src/models.py

### Step 3: Write tests for ChunkRelationship model

Add tests to `tests/test_subsystems.py` for ChunkRelationship:
- Valid chunk_id with "implements" relationship passes
- Valid chunk_id with "uses" relationship passes
- Invalid relationship type (not "implements" or "uses") fails
- Empty chunk_id fails
- Invalid chunk_id format fails (should match `{NNNN}-{short_name}` pattern)

Location: tests/test_subsystems.py

### Step 4: Implement ChunkRelationship model

Add ChunkRelationship to `src/models.py`:
- `chunk_id: str` with validator for `{NNNN}-{short_name}` pattern
- `relationship: Literal["implements", "uses"]`

Location: src/models.py

### Step 5: Write tests for SubsystemFrontmatter model

Add tests to `tests/test_subsystems.py` for SubsystemFrontmatter:
- Valid frontmatter with all fields passes
- Valid frontmatter with empty chunks list passes
- Valid frontmatter with empty code_references list passes
- Invalid status value fails
- Invalid chunk relationship fails (propagates from ChunkRelationship)
- Invalid code reference fails (propagates from SymbolicReference)

Location: tests/test_subsystems.py

### Step 6: Implement SubsystemFrontmatter model

Add SubsystemFrontmatter to `src/models.py`:
- `status: SubsystemStatus`
- `chunks: list[ChunkRelationship]` (defaults to empty list)
- `code_references: list[SymbolicReference]` (defaults to empty list)

Location: src/models.py

### Step 7: Write tests for Subsystems utility class

Add tests to `tests/test_subsystems.py` for the Subsystems class:
- `subsystems_dir` property returns `docs/subsystems/` path
- `enumerate_subsystems()` returns empty list when no subsystems exist
- `enumerate_subsystems()` returns list of subsystem directory names when subsystems exist
- `is_subsystem_dir()` returns True for valid pattern (`0001-validation`)
- `is_subsystem_dir()` returns False for invalid patterns (`invalid`, `001-short`, `0001_underscore`)
- `parse_subsystem_frontmatter()` returns validated frontmatter for valid subsystem
- `parse_subsystem_frontmatter()` returns None for non-existent subsystem

Location: tests/test_subsystems.py

### Step 8: Implement Subsystems utility class

Create `src/subsystems.py` with the Subsystems class:
- `__init__(project_dir)`: Store project directory
- `subsystems_dir` property: Return `project_dir / "docs" / "subsystems"`
- `enumerate_subsystems()`: List directories in subsystems_dir
- `is_subsystem_dir(name)`: Match `{NNNN}-{short_name}` pattern using regex
- `parse_subsystem_frontmatter(subsystem_id)`: Read OVERVIEW.md, extract YAML frontmatter, validate with SubsystemFrontmatter model

Location: src/subsystems.py

### Step 9: Run all tests and verify

Run the full test suite to ensure:
- All new tests pass
- No regressions in existing tests

Command: `pytest tests/`

## Dependencies

No external dependencies beyond what's already in the project:
- Pydantic (already used in models.py)
- PyYAML (already used for frontmatter parsing in chunks.py)

## Risks and Open Questions

- **Chunk ID validation regex**: The chunk ID pattern `{NNNN}-{short_name}` needs to match what `Chunks.enumerate_chunks()` accepts. Review `src/chunks.py` to ensure consistency.
- **Frontmatter parsing**: The YAML frontmatter extraction pattern in `Chunks.parse_chunk_frontmatter()` should be reusable or extracted to a shared utility to avoid duplication.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->