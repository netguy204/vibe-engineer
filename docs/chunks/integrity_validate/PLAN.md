# Implementation Plan

## Approach

Created a new `src/integrity.py` module that implements file-based referential integrity validation following the approach documented in the `docs/investigations/referential_integrity/` investigation.

Key design decisions:
- **Stateless file-based validation**: Build an in-memory artifact index on each run, validate, discard. No persistent database needed.
- **Single traversal**: All validation done in one pass through artifacts and source files.
- **Error/warning separation**: Errors block validation (exit code 1), warnings are informational.
- **Clear error messages**: Each error identifies source file, target reference, link type, and human-readable message.

Building on existing patterns:
- Reuses existing frontmatter parsers from `chunks.py`, `narratives.py`, `investigations.py`, `subsystems.py`, and `friction.py`
- Reuses `CHUNK_BACKREF_PATTERN` and `SUBSYSTEM_BACKREF_PATTERN` from `chunks.py` for code scanning
- Follows click CLI patterns from existing `ve.py` commands

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk USES the workflow artifact managers (Chunks, Narratives, etc.) for enumeration and frontmatter parsing.

## Sequence

### Step 1: Create integrity.py module

Created `src/integrity.py` with:
- `IntegrityError` and `IntegrityWarning` dataclasses for structured error reporting
- `IntegrityResult` dataclass with success status, errors, warnings, and statistics
- `IntegrityValidator` class that:
  1. Builds in-memory artifact index
  2. Validates chunk outbound refs (narrative, investigation, subsystems, friction entries, depends_on)
  3. Validates proposed_chunks in narratives, investigations, and friction log
  4. Validates subsystem chunk references
  5. Validates code backreferences (# Chunk: and # Subsystem: comments)

### Step 2: Add CLI command to ve.py

Added `ve validate` command after `ve init`:
- `--verbose` flag for detailed statistics
- `--strict` flag to treat warnings as errors
- Returns exit code 1 if errors found
- Clear output format with link types and file paths

### Step 3: Write comprehensive tests

Created `tests/test_integrity.py` with 28 tests covering:
- Empty project validation
- Valid chunk references (narrative, investigation, subsystem, friction)
- Invalid references (all link types)
- proposed_chunks validation in narratives, investigations, friction
- Code backreference validation (both chunk and subsystem)
- Multiple errors detection
- CLI interface tests

## Dependencies

No new external dependencies required. Uses existing modules:
- `chunks.py` for Chunks class and backref patterns
- `narratives.py`, `investigations.py`, `subsystems.py`, `friction.py` for artifact managers

## Risks and Open Questions

None remaining - implementation complete and tested.

## Deviations

- **Prototype not available**: The investigation referenced `prototypes/file_validator.py` but this file didn't exist in the worktree. Implemented from scratch following the investigation's documented approach and existing code patterns.
