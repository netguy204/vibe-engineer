---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/frontmatter.py
- tests/test_frontmatter.py
- src/chunks.py
- src/narratives.py
- src/investigations.py
- src/subsystems.py
- src/friction.py
- src/artifact_ordering.py
code_references:
- ref: src/frontmatter.py
  implements: Shared frontmatter I/O module - unified interface for parsing and updating
    YAML frontmatter
- ref: src/frontmatter.py#parse_frontmatter
  implements: Parse YAML frontmatter from file and validate with Pydantic model
- ref: src/frontmatter.py#parse_frontmatter_with_errors
  implements: Parse frontmatter with detailed error messages for validation reporting
- ref: src/frontmatter.py#parse_frontmatter_from_content
  implements: Parse frontmatter from content string (cache-based resolution)
- ref: src/frontmatter.py#parse_frontmatter_from_content_with_errors
  implements: Parse frontmatter from content string with error details
- ref: src/frontmatter.py#extract_frontmatter_dict
  implements: Extract raw frontmatter dict without Pydantic validation (generic field
    extraction)
- ref: src/frontmatter.py#update_frontmatter_field
  implements: Update a single field in file's YAML frontmatter
- ref: src/chunks.py#Chunks::parse_chunk_frontmatter_with_errors
  implements: Migrated to use shared parse_frontmatter_with_errors
- ref: src/chunks.py#Chunks::_parse_frontmatter_from_content
  implements: Migrated to use shared parse_frontmatter_from_content
- ref: src/narratives.py#Narratives::parse_narrative_frontmatter
  implements: Migrated to use shared extract_frontmatter_dict with legacy field remapping
- ref: src/investigations.py#Investigations::parse_investigation_frontmatter
  implements: Migrated to use shared parse_frontmatter
- ref: src/subsystems.py#Subsystems::parse_subsystem_frontmatter
  implements: Migrated to use shared parse_frontmatter
- ref: src/friction.py#Friction::parse_frontmatter
  implements: Migrated to use shared parse_frontmatter as parse_fm
- ref: src/artifact_ordering.py#_parse_frontmatter
  implements: Migrated to use shared extract_frontmatter_dict
narrative: arch_consolidation
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Extract duplicated YAML frontmatter parsing and updating logic into a single shared utility module (`src/frontmatter.py`). This consolidates ~10 duplicated implementations across chunks.py, narratives.py, investigations.py, subsystems.py, friction.py, and artifact_ordering.py into a unified parse/validate/update interface.

Each artifact module currently implements the same pattern independently:
- Read file content
- Regex match `^---\n(.*?)\n---` to extract frontmatter
- Parse with `yaml.safe_load()`
- Validate with pydantic `model_validate()`
- Update with `_update_overview_frontmatter()` (write pattern)

This duplication creates maintenance burden when the frontmatter format evolves. A shared utility enables consistent behavior, reduces duplication, and provides a single place to enhance frontmatter I/O (e.g., better error messages, validation hooks, or format migrations).

## Success Criteria

- `src/frontmatter.py` module exists with a unified interface for frontmatter I/O
- The module provides `parse_frontmatter(file_path, model_class)` function that:
  - Reads a file and extracts YAML frontmatter using regex `^---\n(.*?)\n---`
  - Parses YAML with `yaml.safe_load()`
  - Validates against the provided pydantic model using `model_validate()`
  - Returns validated model instance or None (with optional error details)
- The module provides `update_frontmatter_field(file_path, field, value)` function that:
  - Reads existing frontmatter and body
  - Updates a single field in the frontmatter dict
  - Reconstructs the file with updated YAML frontmatter
  - Preserves the body content unchanged
- All existing call sites migrated to use the shared utility:
  - `narratives.py`: `parse_narrative_frontmatter()` and `_update_overview_frontmatter()`
  - `investigations.py`: `parse_investigation_frontmatter()` and `_update_overview_frontmatter()`
  - `subsystems.py`: `parse_subsystem_frontmatter()`
  - `chunks.py`: `parse_chunk_frontmatter()`, `parse_chunk_frontmatter_with_errors()`, `_parse_frontmatter_from_content()`
  - `friction.py`: `parse_frontmatter()`
  - `artifact_ordering.py`: `_parse_frontmatter()`
- All existing tests pass with the new shared implementation
- No functional changes to existing behavior (refactor only)


