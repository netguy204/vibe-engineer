---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- tests/test_integrity.py
code_references:
  - ref: src/integrity.py#IntegrityValidator::_build_parent_chunk_index
    implements: "Builds reverse index for narrative→chunk and investigation→chunk lookups"
  - ref: src/integrity.py#IntegrityValidator::_build_chunk_code_index
    implements: "Builds reverse index mapping chunks to their referenced file paths"
  - ref: src/integrity.py#IntegrityValidator::_validate_chunk_outbound
    implements: "Extended with bidirectional checks for chunk↔narrative and chunk↔investigation warnings"
  - ref: src/integrity.py#IntegrityValidator::_validate_code_backreferences
    implements: "Extended with code↔chunk bidirectional warnings"
  - ref: tests/test_integrity.py#TestIntegrityValidatorBidirectional
    implements: "Tests for bidirectional consistency warnings"
narrative: null
investigation: referential_integrity
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- integrity_validate
- integrity_code_backrefs
- integrity_proposed_chunks
created_after:
- orch_dashboard_live_tail
- reviewer_decision_tool
---

# Chunk Goal

## Minor Goal

Add warnings for bidirectional consistency violations:
- Chunk claims a narrative but narrative's proposed_chunks doesn't list the chunk
- Chunk claims an investigation but investigation's proposed_chunks doesn't list the chunk
- Code has `# Chunk:` backref but chunk's code_references doesn't include that file

These should be warnings (not errors) because the parent→child direction is often set at creation time while child→parent is added later.

## Success Criteria

- `ve validate` warns when chunk→narrative link lacks corresponding narrative→chunk link
- `ve validate` warns when chunk→investigation link lacks corresponding investigation→chunk link
- `ve validate` warns when code→chunk backref lacks corresponding chunk→code reference
- Warnings are distinguishable from errors (different exit code or output format)
- `ve validate --strict` flag can promote warnings to errors
- Tests cover bidirectional consistency detection