---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/workspace_validation.py
- tests/test_workspace_validation.py
- tests/test_integrity.py
code_references:
- ref: src/workspace_validation.py#_Validator::check_code_references
  implements: 'Workspace-mode declared-path checking with single-tree parity: directory
    targets accepted, code_paths validated, chunk-status gating'
- ref: tests/test_workspace_validation.py
  implements: Behavior tests for directory acceptance, code_paths rot detection, qualified
    routing, and status gating in workspace mode
- ref: tests/test_integrity.py#TestIntegrityValidatorFilePaths::test_directory_code_reference_exists_clean
  implements: Single-tree pin of the directory-acceptance semantics workspace mode
    matches
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---
# Chunk Goal

## Minor Goal

`ve workspace validate`'s declared-path checking agrees with the single-tree
chunk→file check
(src/integrity.py#IntegrityValidator::_validate_chunk_file_paths), so agents
cannot learn the wrong lesson from either validator.
`_Validator.check_code_references` (src/workspace_validation.py):

- **accepts directory entries** — path existence is tested with `.exists()`,
  not `.is_file()`, because "this chunk governs that package directory" is a
  legitimate reference (field evidence: 7 previously unfixable defects in the
  Cloud Capital platform workspace for existing directories like
  `packages/libs/env-config`);
- **validates `code_paths` entries** alongside `code_references` file parts,
  through one shared resolution path (same qualified-reference routing, same
  existence test, same `unresolvable-frontmatter` fix class, with the defect
  message naming the offending field), so neither field rots invisibly in
  workspace mode;
- **applies the same chunk-status gating** as the single-tree check: only
  ACTIVE and COMPOSITE chunks are held to on-disk existence, because FUTURE
  and IMPLEMENTING chunks legitimately list files they expect to create and
  HISTORICAL/SUPERSEDED chunks keep archaeological references.

Symbol-anchor checking remains a workspace-mode extra on top of that shared
contract and applies only to file targets — a symbol cannot be looked up in a
directory.

## Success Criteria

- `WorkspaceValidator.check_code_references` accepts a `code_references`
  entry whose file part names an existing directory (`.exists()`, not
  `.is_file()`), so "this chunk governs that package directory" validates
  cleanly — the 7 Cloud Capital directory defects become unreproducible.
- Chunk `code_paths` entries are validated in workspace mode: a stale
  `code_paths` path on an ACTIVE/COMPOSITE chunk produces an
  `UNRESOLVABLE_FRONTMATTER` defect whose message names the `code_paths`
  field.
- Workspace mode applies the same chunk-status gating as
  `IntegrityValidator._validate_chunk_file_paths`: FUTURE, IMPLEMENTING,
  HISTORICAL, and SUPERSEDED chunks are exempt from declared-path existence
  checks, for the same documented reasons.
- A symbol anchor on a directory target does not crash or false-positive;
  symbol checking applies only to file targets.
- Tests in tests/test_workspace_validation.py cover directory acceptance,
  code_paths rot detection, and status gating; tests/test_integrity.py pins
  the single-tree directory-acceptance semantics the workspace side now
  matches.
- `uv run pytest tests/` passes and `uv run ve validate` is clean.
