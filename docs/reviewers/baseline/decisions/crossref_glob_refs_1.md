---
decision: APPROVE
summary: "Glob patterns in code_paths and code_references file parts are expanded by all four path-existence sites (single-tree integrity, workspace validator, completion gate, shared check_reference_target) with error-only-on-empty-expansion semantics, symbol anchors on patterns honestly reported as uncheckable, and behavior-level tests plus SPEC.md documentation in place."
operator_review: null
---

## Criteria Assessment

### Criterion 1: Glob magic in code_paths / code_references file parts is treated as a pattern by every validator that checks chunk-declared paths

- **Status**: satisfied
- **Evidence**: Shared `is_glob_pattern`/`expand_glob` in `src/symbols.py`; branch points in `src/integrity.py#IntegrityValidator::_validate_chunk_file_paths` (`check()` closure), `src/workspace_validation.py#check_code_references` (`resolve_path` closure), `src/chunk_validation.py#validate_chunk_references_exist` (code_paths loop), and `src/symbols.py#check_reference_target` (covers the gate's code_references loop and subsystem validation).

### Criterion 2: Non-empty expansion is verified; empty expansion is an error naming the pattern

- **Status**: satisfied
- **Evidence**: All four sites error only when `expand_glob` returns an empty list, with messages quoting the pattern ("glob pattern '...' matches nothing"). Malformed patterns degrade to the same empty-expansion error rather than crashing (try/except in `expand_glob`).

### Criterion 3: packages/tasks/*/Dockerfile-style entries validate without enumerating N paths

- **Status**: satisfied
- **Evidence**: The field-evidence pattern is tested verbatim in `tests/test_integrity.py` (test_matching_glob_code_path_is_clean), `tests/test_workspace_validation.py` (test_matching_glob_code_paths_entry_is_clean), and `tests/test_chunk_complete_gate.py` (test_matching_glob_declarations_complete).

### Criterion 4: Symbol anchors on glob file parts are uncheckable (warning/unverified), never silently passed or spuriously failed

- **Status**: satisfied
- **Evidence**: `check_reference_target` returns a warning; the workspace validator appends an `UnverifiedReference` with an explicit reason. Tested in `tests/test_symbols.py` (test_symbol_anchor_on_glob_is_warning) and `tests/test_workspace_validation.py` (test_symbol_anchor_on_glob_pattern_is_unverified).

### Criterion 5: The single-tree validator, workspace validator, and completion gate agree on semantics

- **Status**: satisfied
- **Evidence**: All sites branch on the same `is_glob_pattern` predicate and expand with the same `expand_glob` helper; the workspace parity docstring in `check_code_references` names glob expansion as part of the shared contract.

### Criterion 6: SPEC.md's Code Reference Format documents the glob form

- **Status**: satisfied
- **Evidence**: `docs/trunk/SPEC.md` "Code Reference Format" gained a glob example and a "Glob patterns" paragraph stating the empty-expansion-is-error rule and the uncheckable-symbol-anchor rule.

### Criterion 7: All tests pass and ve validate is clean

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` — 4792 passed. `uv run ve validate` — passes; remaining warnings are the bidirectional-backreference notices for this still-IMPLEMENTING chunk, resolved when code_references are populated at completion.
