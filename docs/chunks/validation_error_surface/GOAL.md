---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/artifact_manager.py
  - src/narratives.py
  - src/investigations.py
  - src/subsystems.py
  - src/chunks.py
  - tests/test_artifact_manager_errors.py
code_references:
  - ref: src/artifact_manager.py#ArtifactManager::parse_frontmatter_with_errors
    implements: "Base class error-surfacing parser that returns tuple of (frontmatter, errors)"
  - ref: src/narratives.py#Narratives::parse_narrative_frontmatter_with_errors
    implements: "Narrative-specific error parser with legacy 'chunks' field mapping"
  - ref: src/investigations.py#Investigations::parse_investigation_frontmatter_with_errors
    implements: "Investigation error parser alias delegating to base class"
  - ref: src/subsystems.py#Subsystems::parse_subsystem_frontmatter_with_errors
    implements: "Subsystem error parser alias delegating to base class"
  - ref: src/chunks.py#plan_has_content
    implements: "Specific exception handling replacing bare except clause"
  - ref: src/chunk_validation.py#plan_has_content
    implements: "Specific exception handling in extracted validation module"
  - ref: tests/test_artifact_manager_errors.py
    implements: "Test coverage for error surfacing methods"
narrative: arch_consolidation
investigation: null
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: implements
friction_entries: []
bug_type: null
depends_on:
- frontmatter_io
- artifact_manager_base
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Surface validation errors consistently across all artifact types to enable better debugging and error reporting when frontmatter parsing fails.

Currently, only `parse_chunk_frontmatter_with_errors()` provides detailed Pydantic validation error messages. All other artifact types (narratives, investigations, subsystems) silently swallow `ValidationError` exceptions at parse time and return None, making it impossible for callers to understand why parsing failed.

Additionally, `plan_has_content()` at chunks.py line 1452 uses a bare `except Exception: return False`, which masks file read errors and other failures.

This chunk establishes a consistent error surfacing convention across all frontmatter parsers, fixing the inconsistent None-vs-ValueError pattern and ensuring validation failures are debuggable.

## Success Criteria

- All artifact frontmatter parsers have `_with_errors` variants that return `tuple[Frontmatter | None, list[str]]`
  - `parse_narrative_frontmatter_with_errors()` added to narratives.py
  - `parse_investigation_frontmatter_with_errors()` added to investigations.py
  - `parse_subsystem_frontmatter_with_errors()` added to subsystems.py

- The bare `except Exception` in `plan_has_content()` (chunks.py:1452) is replaced with specific exception handling for `FileNotFoundError` and `PermissionError`, with other exceptions propagating or being logged

- Error surfacing convention is documented in code comments explaining when to use `_with_errors` variants vs. regular parsers

- Callers that need detailed error messages (validation commands, error reporting, etc.) are updated to use `_with_errors` variants

- All existing tests pass, demonstrating backward compatibility of the regular parsers (which continue to return None on failure)

