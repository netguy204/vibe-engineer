---
decision: APPROVE
summary: "All six success criteria satisfied with direct test evidence: one shared AST-backed predicate (symbols.name_is_reexport_only) reclassifies import/__all__-only mentions as absent across the workspace validator, the chunk validate/complete gate, and `ve exists` (as a distinct reexport_matches evidence class), conservatism is pinned by a 12-case decision table, and the full suite passes 4798/4798 with `ve validate` clean."
operator_review: null
---

## Criteria Assessment

### Criterion 1: A shared AST-backed predicate (in `src/symbols.py`, extending the existing

- **Status**: satisfied
- **Evidence**: `src/symbols.py#name_is_reexport_only` uses the module's existing `ast` machinery (no parallel parser): excluded spans are `ast.Import`/`ast.ImportFrom` node line ranges plus *simple* statements (`Assign`/`AnnAssign`/`AugAssign`/`Expr`) mentioning `__all__`; returns None for non-identifier names and unparseable content so no cleanly-validating file gains a new error. `tests/test_symbols.py::TestNameIsReexportOnly` (12 cases) pins the decision table, including multi-line parenthesized imports, `__all__ +=`/`.append`, and the noqa-comment-on-import-line field idiom.

### Criterion 2: Workspace validation (`_symbol_is_absent` via `check_code_references`)

- **Status**: satisfied
- **Evidence**: `src/workspace_validation.py#_symbol_is_absent` gained `is_python` and now returns `(name, reason)`; the `check_code_references` call site passes `target.suffix == ".py"` and interpolates the reason, so the re-export defect message says the name "appears only in import/__all__ re-export statements; the definition lives in another file" — pointing at the real fix (repoint the ref), not a phantom rename. `tests/test_workspace_validation.py::test_reexport_only_symbol_is_unresolvable_frontmatter` replicates the `# noqa: F401` field case; the `__all__`-only variant also gates as UNRESOLVABLE_FRONTMATTER.

### Criterion 3: The chunk validate/complete gate path (`symbols.check_reference_target`)

- **Status**: satisfied
- **Evidence**: `check_reference_target`'s fallback was restructured to parse once, distinguishing unparseable (warning, unchanged — `test_unparseable_python_is_warning_not_error` still passes) from parseable-defines-nothing (the pure re-export `__init__.py` field case, previously a vague "Could not extract symbols" warning, now a precise error). `TestCheckReferenceTargetReexports` covers re-export-only → error, `__all__`-only → error, try/except-ImportError fallback assignment → warning (unchanged conservatism), and defines-nothing-with-absent-name → error. Unreadable files stay warnings (never provably absent).

### Criterion 4: `ve exists` stays in agreement with the validator (the pinned

- **Status**: satisfied
- **Evidence**: `src/absence.py#ExistenceReport.reexport_matches` is a distinct match class (mirroring how `basename_matches` classifies "moved"): `search_existence` routes a Python file's matches there iff `name_is_reexport_only` — exactly the files the validator calls the name absent in — so `symbol_matches` and the validator can never disagree. Re-export mentions still count toward `found` (they are the moved-to breadcrumb; `test_name_surviving_only_as_reexport_is_still_evidence`). JSON contract test extended with `reexport_matches` + counts; `src/cli/exists_cmd.py` renders a "Re-export mentions (definition elsewhere?)" section (`test_text_output_renders_reexport_mentions_distinctly`); module docstring updates the pinned agreement language.

### Criterion 5: Conservatism is preserved and pinned by tests: a name in a call, string,

- **Status**: satisfied
- **Evidence**: `test_usage_docstring_and_offline_comment_are_false`, `test_import_plus_real_definition_is_false` (including the `Bar = compat_shim(Bar)` dynamic case), `test_compound_statement_mentioning_dunder_all_is_false` (an `if "Bar" in __all__:` guard can never exclude real code), `test_unparseable_content_is_none`, and the pre-existing `test_symbol_appearing_anywhere_in_the_file_is_accepted` (dynamic `make_class` definition) all pass untouched. No resolution logic was added; UNCHECKED reporting for non-identifier anchors remains with crossref_unchecked_anchors.

### Criterion 6: `uv run pytest tests/` and `uv run ve validate` are clean.

- **Status**: satisfied
- **Evidence**: Full suite 4798 passed, 0 failed (baseline: no pre-existing failures inherited). `uv run ve validate` passes; remaining warnings are the expected pre-completion code_references gaps for this chunk, resolved by the completion step.
