---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- tests/test_integrity.py
code_references:
  - ref: src/integrity.py#IntegrityValidator::_validate_code_backreferences
    implements: "Line-by-line scanning of source files for orphaned code backreferences with line number tracking"
  - ref: tests/test_integrity.py#TestIntegrityValidatorCodeBackrefs::test_error_includes_line_number_in_source
    implements: "Test that error source field includes file:line format"
  - ref: tests/test_integrity.py#TestIntegrityValidatorCodeBackrefs::test_error_message_includes_line_number
    implements: "Test that error message text mentions line number"
  - ref: tests/test_integrity.py#TestIntegrityValidatorCodeBackrefs::test_multiple_errors_report_distinct_line_numbers
    implements: "Test that multiple errors in same file report correct distinct line numbers"
  - ref: tests/test_integrity.py#TestIntegrityValidatorCodeBackrefs::test_subsystem_backref_error_includes_line_number
    implements: "Test that subsystem backreference errors also include line numbers"
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

Validate that code backreferences (`# Chunk:` and `# Subsystem:` comments in source code) point to existing artifacts. Currently these comments are parsed but not validated—they can reference chunks or subsystems that have been deleted or renamed.

This extends the `ve validate` command to catch orphaned code backreferences.

## Success Criteria

- `ve validate` detects `# Chunk: docs/chunks/foo` comments where `foo` doesn't exist
- `ve validate` detects `# Subsystem: docs/subsystems/bar` comments where `bar` doesn't exist
- Error messages include file path and line number of the broken backreference
- Tests cover detection of orphaned backreferences