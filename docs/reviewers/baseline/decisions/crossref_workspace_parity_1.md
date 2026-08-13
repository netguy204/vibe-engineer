---
decision: APPROVE
summary: "Workspace validator now matches single-tree declared-path semantics (directory targets via .exists(), code_paths checked, ACTIVE/COMPOSITE gating) with behavior-level tests on both sides; full suite (4718) and ve validate pass."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `WorkspaceValidator.check_code_references` accepts a `code_references` entry whose file part names an existing directory

- **Status**: satisfied
- **Evidence**: src/workspace_validation.py `_Validator.check_code_references` — the shared `resolve_path` closure tests `target.exists()`; `tests/test_workspace_validation.py::test_code_reference_to_an_existing_directory_is_clean` reproduces the Cloud Capital directory case (`src/env-config`) and passes; `test_code_reference_to_a_missing_directory_still_defects` guards against the swap weakening detection.

### Criterion 2: Chunk `code_paths` entries are validated in workspace mode with an `UNRESOLVABLE_FRONTMATTER` defect naming the field

- **Status**: satisfied
- **Evidence**: `code_paths` entries run through the same `resolve_path` helper with `field_name="code_paths"`, so the defect message says "code_paths entry points at ...". `test_stale_code_paths_entry_is_unresolvable_frontmatter` asserts fix class, path, reference, and field name; `test_chunk_with_only_code_paths_is_still_scanned` guards the early-return restructure; `test_qualified_code_paths_entry_is_unverified` pins identical qualified-reference routing for both fields.

### Criterion 3: Workspace mode applies the same chunk-status gating as `IntegrityValidator._validate_chunk_file_paths`

- **Status**: satisfied
- **Evidence**: chunks return early unless status is ACTIVE/COMPOSITE, with the single-tree rationale quoted in the docstring. `test_non_owning_chunk_statuses_are_exempt_from_path_checks` (parametrized over FUTURE/IMPLEMENTING/HISTORICAL/SUPERSEDED) and `test_composite_chunk_paths_are_checked` mirror the single-tree tests `test_non_owning_statuses_skip_check`/`test_composite_chunk_stale_path_errors`. Subsystem scope deliberately unchanged (`test_subsystem_code_references_are_checked_regardless_of_status`) — single-tree has no competing subsystem check, so no disagreement exists to reconcile.

### Criterion 4: A symbol anchor on a directory target does not crash or false-positive

- **Status**: satisfied
- **Evidence**: symbol lookup is guarded by `target.is_file()` (explicit, not the prior IsADirectoryError-is-an-OSError accident); `test_symbol_anchor_on_a_directory_target_is_skipped` passes.

### Criterion 5: Tests cover directory acceptance, code_paths rot, status gating; single-tree pin exists

- **Status**: satisfied
- **Evidence**: ten new tests in tests/test_workspace_validation.py (parity section); `tests/test_integrity.py::TestIntegrityValidatorFilePaths::test_directory_code_reference_exists_clean` pins the single-tree directory semantics for code_references file parts (code_paths pin pre-existed from crossref_rename_integrity).

### Criterion 6: `uv run pytest tests/` passes and `uv run ve validate` is clean

- **Status**: satisfied
- **Evidence**: 4718 passed; `ve validate` passes with 3 pre-existing warnings inherited from main (crossref_rename_integrity artifacts), none introduced by this chunk.

## Observations (non-blocking)

- Doc drift, deliberately left for a follow-up to avoid colliding with the
  concurrent `crossref_pointer_guard` chunk (which owns edits to
  `src/templates/plugin/skills/workspace-validate-fix.md.jinja2`): that skill
  and `docs/trunk/EXTERNAL.md` describe `unresolvable-frontmatter` as "a
  `code_references` entry"; `code_paths` entries can now also produce the
  class. The defect message itself names the field, so fix loops are not
  misled.
- Qualified (`::`) code references on non-owning chunks no longer appear in
  `report.unverified` (the status gate exempts the whole chunk). Consistent
  with the parity rationale: non-owning chunks are exempt from declared-path
  scrutiny entirely.
