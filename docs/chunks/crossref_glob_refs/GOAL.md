---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/symbols.py
- src/integrity.py
- src/workspace_validation.py
- src/chunk_validation.py
- docs/trunk/SPEC.md
- tests/test_symbols.py
- tests/test_integrity.py
- tests/test_workspace_validation.py
- tests/test_chunk_complete_gate.py
code_references:
- ref: src/symbols.py#is_glob_pattern
  implements: Glob-magic detection shared by every path validator
- ref: src/symbols.py#expand_glob
  implements: Shared glob expansion; malformed patterns degrade to an empty expansion
    instead of crashing
- ref: src/symbols.py#check_reference_target
  implements: 'Glob dispositions in the shared existence check: empty expansion is
    an error, symbol anchors on patterns are uncheckable warnings'
- ref: src/integrity.py#IntegrityValidator::_validate_chunk_file_paths
  implements: Single-tree glob checking for code_paths and code_references file parts
- ref: src/chunk_validation.py#validate_chunk_references_exist
  implements: Completion-gate glob checking for code_paths entries
- ref: src/workspace_validation.py#_Validator::check_code_references
  implements: Workspace-mode glob checking; symbol anchors on patterns routed to unverified
- ref: tests/test_symbols.py#TestCheckReferenceTargetGlobs
  implements: Glob disposition tests for the shared existence check
- ref: tests/test_integrity.py
  implements: Single-tree glob tests (matching pattern clean, empty pattern errors)
- ref: tests/test_workspace_validation.py
  implements: Workspace glob tests including the unverified symbol-anchor disposition
- ref: tests/test_chunk_complete_gate.py
  implements: Completion-gate glob tests (matching globs land, empty globs block)
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on:
- crossref_workspace_parity
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---
# Chunk Goal

## Minor Goal

Chunk `code_paths` entries and `code_references` file parts accept glob patterns (e.g. `packages/tasks/*/Dockerfile`). Every validator that checks chunk-declared paths — `IntegrityValidator._validate_chunk_file_paths` (single-tree `ve validate`), `WorkspaceValidator.check_code_references` (workspace mode), and the completion gate (`validate_chunk_references_exist` / `check_reference_target`, shared with subsystem validation) — expands the pattern through one shared helper and errors only when the expansion is empty. "This change applies uniformly across N packages" is therefore expressible without enumerating N paths that rot independently (field evidence: 5 unfixable defects where rewriting to ~20 concrete paths would be wrong and unmaintainable). Symbol anchors on glob patterns are reported as uncheckable (warning/unverified), never silently passed and never spuriously failed.

## Success Criteria

- A `code_paths` entry or `code_references` file part containing glob magic
  (`*`, `?`, `[`) is treated as a pattern by every validator that checks
  chunk-declared paths: `IntegrityValidator._validate_chunk_file_paths`
  (single-tree `ve validate`), `WorkspaceValidator.check_code_references`
  (workspace mode), and the completion gate
  (`validate_chunk_references_exist` / `check_reference_target`).
- A pattern that matches at least one existing path is a verified reference;
  a pattern whose expansion is empty is an error naming the pattern.
- `packages/tasks/*/Dockerfile`-style entries validate without enumerating N
  concrete paths (the field-evidence case).
- Symbol anchors on glob file parts are reported as uncheckable (warning /
  unverified), never silently passed and never spuriously failed.
- The single-tree validator, the workspace validator, and the completion gate
  agree on these semantics, so no flow teaches a contradictory lesson.
- SPEC.md's Code Reference Format documents the glob form.
- All tests pass (`uv run pytest tests/`) and `uv run ve validate` is clean.

## Rejected Ideas

### Resolve symbol anchors across glob expansions

A ref like `packages/*/handler.py#Handler` could be checked by requiring the
symbol in every (or at least one) matched file.

Rejected because: the goal fixes the error condition to "expansion is empty"
only, and either cross-expansion semantic would guess at intent the reference
format does not express. Symbol anchors on glob refs are reported as
uncheckable instead — honest reporting without invented resolution logic
(the crossref_unchecked_anchors chunk owns that reporting direction).