---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- tests/test_integrity.py
code_references:
  - ref: src/integrity.py#IntegrityValidator::__init__
    implements: "Subsystem→chunk reverse index attribute (_subsystem_chunks) for bidirectional validation"
  - ref: src/integrity.py#IntegrityValidator::_build_parent_chunk_index
    implements: "Building subsystem→chunk index from subsystem frontmatter chunks field"
  - ref: src/integrity.py#IntegrityValidator::_validate_chunk_outbound
    implements: "Chunk→subsystem bidirectional check when chunk references a subsystem"
  - ref: src/integrity.py#IntegrityValidator::_validate_subsystem_chunk_refs
    implements: "Subsystem→chunk bidirectional check when subsystem lists a chunk"
  - ref: tests/test_integrity.py#TestIntegrityValidatorChunkSubsystemBidirectional
    implements: "Test coverage for chunk↔subsystem bidirectional warnings"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Complete the bidirectional integrity checking in `src/integrity.py` by adding chunk↔subsystem validation. Currently, the integrity validator checks bidirectional consistency for chunk↔narrative and chunk↔investigation relationships (emitting warnings when one side references the other but not vice versa), but does not perform the same check for chunk↔subsystem relationships.

This creates a gap where a chunk's `subsystems` field can reference a subsystem that doesn't list the chunk back in its `chunks` field, or vice versa, with no warning emitted. This asymmetry makes it harder to maintain accurate cross-references and can lead to orphaned references in the documentation.

Adding this check completes the referential integrity system and ensures all bidirectional artifact relationships are validated consistently.

## Success Criteria

1. **Subsystem→chunk index built**: `_build_parent_chunk_index()` populates a `_subsystem_chunks` dict mapping subsystem_name → set of chunk_ids listed in the subsystem's `chunks` frontmatter field

2. **Chunk→subsystem bidirectional warning**: When a chunk references a subsystem via its `subsystems` field, but that subsystem's `chunks` field doesn't list the chunk back, emit an `IntegrityWarning` with link_type `chunk↔subsystem`

3. **Subsystem→chunk bidirectional warning**: When a subsystem lists a chunk in its `chunks` field, but that chunk's `subsystems` field doesn't reference the subsystem back, emit an `IntegrityWarning` with link_type `subsystem↔chunk`

4. **Consistent with existing patterns**: The implementation follows the same pattern as the existing chunk↔narrative and chunk↔investigation bidirectional checks (lines 308-342 in `src/integrity.py`)

5. **Test coverage**: `ve chunk validate` emits appropriate warnings for asymmetric chunk↔subsystem references in both directions


