---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- src/ve.py
- tests/test_integrity.py
code_references:
  - ref: src/integrity.py#IntegrityError
    implements: "Data class for referential integrity errors"
  - ref: src/integrity.py#IntegrityWarning
    implements: "Data class for referential integrity warnings (non-fatal)"
  - ref: src/integrity.py#IntegrityResult
    implements: "Result container with success status, errors, warnings, and statistics"
  - ref: src/integrity.py#IntegrityValidator
    implements: "Core validator class for project-wide artifact reference validation"
  - ref: src/integrity.py#IntegrityValidator::validate
    implements: "Main validation entry point orchestrating all checks"
  - ref: src/integrity.py#IntegrityValidator::_validate_chunk_outbound
    implements: "Validates chunk→narrative, chunk→investigation, chunk→subsystem, chunk→friction, chunk→chunk references"
  - ref: src/integrity.py#IntegrityValidator::_validate_narrative_chunk_refs
    implements: "Validates narrative proposed_chunks→chunk references"
  - ref: src/integrity.py#IntegrityValidator::_validate_investigation_chunk_refs
    implements: "Validates investigation proposed_chunks→chunk references"
  - ref: src/integrity.py#IntegrityValidator::_validate_subsystem_chunk_refs
    implements: "Validates subsystem→chunk references"
  - ref: src/integrity.py#IntegrityValidator::_validate_friction_chunk_refs
    implements: "Validates friction log proposed_chunks→chunk references"
  - ref: src/integrity.py#IntegrityValidator::_validate_code_backreferences
    implements: "Validates code→chunk and code→subsystem backreferences in source files"
  - ref: src/integrity.py#validate_integrity
    implements: "Convenience function for running integrity validation"
  - ref: src/ve.py#validate
    implements: "CLI command: ve validate for project-wide referential integrity validation"
  - ref: tests/test_integrity.py
    implements: "Comprehensive test suite covering all validation scenarios"
  - ref: src/cli/init_cmd.py#validate
    implements: "CLI validate command after CLI modularization"
narrative: null
investigation: referential_integrity
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_dashboard_live_tail
- reviewer_decision_tool
---

# Chunk Goal

## Minor Goal

Add a `ve validate` command that runs referential integrity validation across all artifacts and code backreferences. This is the foundation for mechanical guarantees that the reference graph remains consistent.

See `docs/investigations/referential_integrity/` for context, including:
- Complete mapping of 12 link types in the reference graph
- Working prototype in `prototypes/file_validator.py`
- Performance benchmarks (~300ms for full validation)

## Success Criteria

- `ve validate` command exists and can be invoked from CLI
- Validates all artifact link types identified in the investigation
- Returns non-zero exit code when errors are found
- Outputs clear, actionable error messages identifying source and target of broken links
- Completes in <1 second for typical project sizes (suitable for git hooks)
- Tests cover the validation logic