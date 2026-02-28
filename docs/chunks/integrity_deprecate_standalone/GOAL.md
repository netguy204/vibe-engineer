---
status: SUPERSEDED
superseded_by: integrity_deprecated_removal
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- src/chunks.py
- tests/test_integrity.py
code_references:
  - ref: src/integrity.py#IntegrityValidator::validate_chunk
    implements: "Public single-chunk validation entry point for unified validation routing"
  - ref: src/integrity.py#_errors_to_messages
    implements: "Helper to convert IntegrityError objects to string messages for backward compatibility"
  - ref: src/chunks.py#Chunks::validate_subsystem_refs
    implements: "Wrapper method routing through IntegrityValidator"
  - ref: src/chunks.py#Chunks::validate_investigation_ref
    implements: "Wrapper method routing through IntegrityValidator"
  - ref: src/chunks.py#Chunks::validate_narrative_ref
    implements: "Wrapper method routing through IntegrityValidator"
  - ref: src/chunks.py#Chunks::validate_friction_entries_ref
    implements: "Wrapper method routing through IntegrityValidator"
  - ref: tests/test_integrity.py#TestIntegrityValidatorSingleChunk
    implements: "Tests for IntegrityValidator.validate_chunk() single-chunk validation"
narrative: arch_review_remediation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- chunks_class_decouple
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

This chunk deprecates four standalone integrity functions in `src/integrity.py` (lines ~678-858) that duplicate logic already present in the `IntegrityValidator` class: `validate_chunk_subsystem_refs`, `validate_chunk_investigation_ref`, `validate_chunk_narrative_ref`, and `validate_chunk_friction_entries_ref`. Each of these functions creates a new `Chunks()` instance, parses frontmatter independently, and checks the same references that `IntegrityValidator._validate_chunk_outbound` already validates.

The fix routes all callers through the `IntegrityValidator` or extracts a shared implementation that both the standalone functions and the validator use. This eliminates duplicated validation logic and redundant `Chunks()` instantiation.

This chunk depends on `chunks_class_decouple` because that chunk restructures the `Chunks` class and breaks the circular imports that these standalone functions were partly designed to work around. Once that decoupling is in place, there is no longer a reason to maintain the standalone functions as a separate code path.

## Success Criteria

- The four standalone validation functions (`validate_chunk_subsystem_refs`, `validate_chunk_investigation_ref`, `validate_chunk_narrative_ref`, `validate_chunk_friction_entries_ref`) are removed or clearly deprecated
- All callers of these functions route through `IntegrityValidator` or a shared implementation
- No duplicate `Chunks()` instantiation for validation purposes
- Validation behavior is preserved — same errors and warnings are produced
- All integrity and validation tests pass

