---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- tests/test_integrity.py
code_references:
  - ref: tests/test_integrity.py#TestIntegrityValidatorProposedChunks::test_friction_valid_chunk_directory_passes
    implements: "Test friction log with valid chunk_directory references passes validation"
  - ref: tests/test_integrity.py#TestIntegrityValidatorProposedChunks::test_friction_invalid_chunk_directory_fails
    implements: "Test friction log with stale chunk_directory reference fails with appropriate error"
  - ref: tests/test_integrity.py#TestIntegrityValidatorProposedChunks::test_friction_null_chunk_directory_passes
    implements: "Test friction log with null chunk_directory (chunk not yet created) passes validation"
  - ref: tests/test_integrity.py#TestIntegrityValidatorProposedChunks::test_friction_malformed_chunk_directory_detected
    implements: "Test friction log with docs/chunks/ prefix is detected as malformed"
narrative: null
investigation: referential_integrity
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- integrity_validate
created_after:
- orch_dashboard_live_tail
- reviewer_decision_tool
---

# Chunk Goal

## Minor Goal

Validate that `proposed_chunks[].chunk_directory` references in narratives, investigations, and the friction log point to existing chunks. Currently these fields can become stale if a chunk is renamed or deleted.

Note: A null/missing `chunk_directory` is valid (chunk not yet created). Only validate non-null references.

## Success Criteria

- `ve validate` detects stale `chunk_directory` references in narrative OVERVIEW.md files
- `ve validate` detects stale `chunk_directory` references in investigation OVERVIEW.md files
- `ve validate` detects stale `chunk_directory` references in FRICTION.md
- Error messages identify the parent artifact and the broken chunk reference
- Tests cover detection of stale proposed_chunks references