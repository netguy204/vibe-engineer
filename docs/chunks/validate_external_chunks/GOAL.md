---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- src/cli/init_cmd.py
- tests/test_integrity.py
code_references:
  - ref: src/integrity.py#IntegrityResult
    implements: "Added external_chunks_skipped field to track skipped external chunks"
  - ref: src/integrity.py#IntegrityValidator::_build_artifact_index
    implements: "Detection and separation of local vs external chunks during indexing"
  - ref: src/integrity.py#IntegrityValidator::_validate_code_backreferences
    implements: "External chunk recognition for code backref validation"
  - ref: tests/test_integrity.py#write_external_chunk
    implements: "Test helper for creating external chunk fixtures"
  - ref: tests/test_integrity.py#TestIntegrityValidatorExternalChunks
    implements: "Test coverage for external chunk validation scenarios"
  - ref: src/cli/init_cmd.py#validate
    implements: "CLI validate command with external chunk skip reporting in verbose output"
narrative: null
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: uses
- subsystem_id: cross_repo_operations
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- reviewer_init_templates
- integrity_bidirectional
- integrity_code_backrefs
- integrity_fix_existing
- integrity_proposed_chunks
- integrity_validate
- orch_reviewer_decision_mcp
---

# Chunk Goal

## Minor Goal

The `ve validate` command fails when encountering external chunks because it attempts to parse frontmatter from `GOAL.md`, which doesn't exist for external chunks (they have `external.yaml` instead).

This chunk makes validation handle external chunks correctly by:
1. Detecting when a chunk directory contains `external.yaml` instead of `GOAL.md`
2. Either skipping validation for external chunks (minimal fix) or dereferencing the external pointer to validate the canonical artifact (full solution)

This enables `ve validate` to run successfully on repositories that contain external chunk references, which is essential for multi-repository workflows.

## Success Criteria

- `ve validate` succeeds when the chunks directory contains external chunks
- External chunks are clearly identified in validation output (e.g., "Skipping external chunk: xr_ve_worktrees_flag")
- Local chunks continue to be validated as before
- Tests cover both external and local chunk validation scenarios