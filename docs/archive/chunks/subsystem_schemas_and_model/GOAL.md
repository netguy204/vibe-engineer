---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/subsystems.py
- tests/test_subsystems.py
code_references:
- ref: src/models.py#SubsystemStatus
  implements: Status enum for subsystem documentation lifecycle (DISCOVERING, DOCUMENTED,
    REFACTORING, STABLE, DEPRECATED)
- ref: src/models.py#ChunkRelationship
  implements: Model for chunk-to-subsystem relationships with implements/uses distinction
- ref: src/models.py#ChunkRelationship::validate_chunk_id
  implements: Validation of chunk_id format ({NNNN}-{short_name} pattern)
- ref: src/models.py#SubsystemFrontmatter
  implements: Frontmatter schema for subsystem OVERVIEW.md files
- ref: src/subsystems.py#Subsystems
  implements: Utility class for subsystem documentation management
- ref: src/subsystems.py#Subsystems::subsystems_dir
  implements: Property returning path to docs/subsystems/
- ref: src/subsystems.py#Subsystems::enumerate_subsystems
  implements: List subsystem directory names
- ref: src/subsystems.py#Subsystems::is_subsystem_dir
  implements: Validate {NNNN}-{short_name} directory pattern
- ref: src/subsystems.py#Subsystems::parse_subsystem_frontmatter
  implements: Parse and validate OVERVIEW.md frontmatter
- ref: tests/test_subsystems.py#TestChunkRelationship
  implements: Unit tests for ChunkRelationship validation
- ref: tests/test_subsystems.py#TestSubsystemFrontmatter
  implements: Unit tests for SubsystemFrontmatter validation
- ref: tests/test_subsystems.py#TestSubsystems
  implements: Unit tests for Subsystems utility class
narrative: subsystem_documentation
created_after:
- future_chunk_creation
---

# Chunk Goal

## Minor Goal

Define the data model for subsystem documentation—a new artifact type that captures cross-cutting patterns that emerge organically as the codebase evolves.

This chunk establishes the foundational schemas that subsequent chunks will build upon. Without a clear data model, the CLI commands (chunk 2), templates (chunk 3), and bidirectional references (chunk 4) cannot be implemented consistently.

This advances the trunk goal's **Required Properties** by enabling agents to recognize existing subsystems rather than reinventing patterns, which keeps document maintenance manageable over time.

## Success Criteria

1. **SubsystemStatus enum** exists with values: `DISCOVERING`, `DOCUMENTED`, `REFACTORING`, `STABLE`, `DEPRECATED`

2. **ChunkRelationship model** captures the implements/uses distinction:
   - `chunk_id`: The chunk directory name (e.g., `0003-feature_name`)
   - `relationship`: Either `implements` or `uses`

3. **SubsystemFrontmatter model** validates subsystem OVERVIEW.md frontmatter:
   - `status`: SubsystemStatus enum
   - `chunks`: List of ChunkRelationship entries
   - `code_references`: List of SymbolicReference (reusing existing model from src/models.py)

4. **Subsystems class** provides utility functions:
   - `__init__(project_dir)`: Initialize with project directory
   - `subsystems_dir` property: Returns path to `docs/subsystems/`
   - `enumerate_subsystems()`: List subsystem directory names
   - `is_subsystem_dir(name)`: Check if a directory matches the `{NNNN}-{short_name}` pattern
   - `parse_subsystem_frontmatter(subsystem_id)`: Parse and validate OVERVIEW.md frontmatter

5. **All models** are added to `src/models.py` following existing Pydantic patterns

6. **Subsystems class** is added to a new `src/subsystems.py` following the `Chunks` and `Narratives` class patterns

7. **Unit tests** validate:
   - SubsystemStatus enum values
   - ChunkRelationship validation (valid/invalid chunk IDs, relationship types)
   - SubsystemFrontmatter validation with various inputs
   - Subsystems utility methods