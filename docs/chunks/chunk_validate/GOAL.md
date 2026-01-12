---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/chunks.py
- src/models.py
- tests/test_chunk_validate.py
code_references:
- ref: src/models.py#SymbolicReference
  implements: Pydantic model for symbolic code references with validation
- ref: src/chunks.py#ValidationResult
  implements: Dataclass for structured error reporting
- ref: src/chunks.py#Chunks::validate_chunk_complete
  implements: Status, code_references, subsystem, investigation, and narrative validation
- ref: src/chunks.py#Chunks::validate_investigation_ref
  implements: Validation that referenced investigations exist
- ref: src/chunks.py#Chunks::validate_narrative_ref
  implements: Validation that referenced narratives exist
- ref: src/chunks.py#Chunks::_validate_symbol_exists
  implements: Symbol existence verification for code references
- ref: src/ve.py#validate
  implements: CLI command interface - chunk validate command
- ref: tests/test_chunk_validate.py#TestInvestigationRefValidation
  implements: Test coverage for investigation reference validation
- ref: tests/test_chunk_validate.py#TestSymbolicReferenceValidation
  implements: Test coverage for symbolic reference validation
- ref: tests/test_chunk_validate.py#TestNarrativeRefValidation
  implements: Test coverage for narrative reference validation
created_after:
- chunk_overlap_command
---

# Chunk Goal

## Minor Goal

Implement `ve chunk complete [chunk_id]` to validate that a chunk's metadata is ready for completion. This command verifies the chunk status is `IMPLEMENTING` or `ACTIVE` and that its `code_references` field is properly structured per the defined schema. The command uses Pydantic models for validation, providing clear, actionable error messages that agents can use to correct formatting mistakes.

This command is a verification checkpoint in the chunk lifecycle. The `/chunk-complete` skill workflow will call this command to validate metadata before triggering the subsequent overlap detection and reference resolution steps. By separating validation from mutation, agents can iterate on metadata correctness before committing changes.

## Success Criteria

### Command Interface

- `ve chunk complete [chunk_id]` command exists
- `chunk_id` argument is optional; defaults to latest chunk if omitted
- Supports `--project-dir` option to specify target project

### Status Validation

- Command fails if chunk's `status` field is not `IMPLEMENTING` or `ACTIVE`
- Error message clearly states the current status and explains why completion is blocked
- Exit code non-zero on validation failure

### Code References Validation

- Command validates `code_references` field using Pydantic models
- Validates structure: list of objects with `file` (string) and `ranges` (list) fields
- Validates each range: must have `lines` (string in "N-M" or "N" format) and `implements` (string) fields
- On malformed data, outputs Pydantic's validation errors in a readable format
- Error output should be structured enough for agents to identify and fix specific issues

### Pydantic Model Definition

- `CodeRange` model: `lines` (string), `implements` (string)
- `CodeReference` model: `file` (string), `ranges` (list of `CodeRange`)
- Models use Pydantic v2 syntax
- Models should be defined in a module importable by both the CLI and tests

### Success Output

- On successful validation, prints confirmation message
- Exit code 0 on success

### Error Output Requirements

- Validation errors include field path (e.g., `code_references[0].ranges[1].lines`)
- Errors explain what was wrong (e.g., "expected string, got int")
- Multiple errors are reported together (not just the first one)
- Errors are formatted for agent consumption (structured, parseable)