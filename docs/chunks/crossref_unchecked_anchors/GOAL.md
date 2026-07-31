---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/symbols.py
- src/workspace_validation.py
- src/cli/workspace.py
- src/integrity.py
- src/cli/init_cmd.py
- tests/test_symbols.py
- tests/test_workspace_validation.py
- tests/test_integrity.py
- tests/test_chunk_complete_gate.py
code_references:
- ref: src/symbols.py#check_reference_target
  implements: UNCHECKED warnings for non-Python file anchors and non-identifier anchors
    in single-tree mode
- ref: src/workspace_validation.py#_symbol_is_absent
  implements: 'Disposition-tagged result: absent, unchecked, or may-exist'
- ref: src/workspace_validation.py#_Validator::check_code_references
  implements: Routes every uncheckable anchor into UnverifiedReference and counts
    symbol-anchor coverage
- ref: src/workspace_validation.py#ValidationReport
  implements: symbol_anchors_checked/unchecked coverage counts in the report and its
    JSON counts block
- ref: src/cli/workspace.py#_render_report
  implements: Symbol-anchor coverage line and generalized unverified summary in text
    output
- ref: src/integrity.py#IntegrityResult
  implements: symbol_anchors_unchecked count on the single-tree result
- ref: src/integrity.py#IntegrityValidator::_validate_chunk_file_paths
  implements: Counts symbol anchors ve validate walks past without checking
- ref: src/cli/init_cmd.py#validate
  implements: ve validate output line stating unchecked symbol anchors and where symbol
    checking runs
- ref: tests/test_symbols.py
  implements: Pins UNCHECKED warnings from check_reference_target
- ref: tests/test_workspace_validation.py
  implements: Pins unverified entries and coverage counts in workspace mode
- ref: tests/test_integrity.py
  implements: Pins the ve validate unchecked count and CLI line
- ref: tests/test_chunk_complete_gate.py
  implements: Pins that UNCHECKED never gates completion
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on:
- crossref_reexport_absence
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---
# Chunk Goal

## Minor Goal

The symbol checkers report every anchor they cannot check as an explicit UNCHECKED disposition instead of silently passing it. An anchor whose last `::` component fails `str.isidentifier()` — the dotted/bracketed shape of YAML workflow paths like `jobs.Checks.steps[Seed workspace .venv]`, the same undecidable signal that makes `name_is_reexport_only` return `None` — is routed into the existing unverified mechanism in workspace mode (`_symbol_is_absent` returns a tagged `unchecked` disposition) and into the warning channel in single-tree mode (`check_reference_target`, which also states non-Python file anchors rather than skipping them). Both `ve workspace validate` (checked/unchecked coverage counts in text and JSON, folding in the glob-anchor, directory-target, unreadable-target, and cross-repo dispositions) and `ve validate` (a count of the symbol anchors it walks past, since it verifies file parts only) surface what the symbol checker is not seeing. UNCHECKED is honest reporting only: it never gates, and no new resolution logic exists.

## Success Criteria

- `ve workspace validate`: a `code_references` symbol anchor whose last `::`
  component fails `str.isidentifier()` (e.g. `jobs.Checks.steps[Seed
  workspace .venv]`) produces an `UnverifiedReference` entry with a stated
  reason — the same mechanism `crossref_glob_refs` uses for glob-pattern
  anchors — never a silent pass and never a defect.
- The UNCHECKED signal is `str.isidentifier()` on the anchor leaf: the same
  undecidable signal that makes `name_is_reexport_only` return `None`, not a
  parallel predicate.
- `ValidationReport` carries `symbol_anchors_checked` and
  `symbol_anchors_unchecked` counts, present in both the JSON `counts` block
  and the `ve workspace validate` text output; existing uncheckable
  dispositions (glob anchors, cross-repo-qualified anchors, directory
  targets, unreadable targets) fold into the unchecked count rather than
  gaining a second mechanism.
- `check_reference_target` (single-tree: `ve chunk validate`, the completion
  gate, `ve subsystem validate`) reports symbol anchors on non-Python files
  and non-identifier anchors on Python files as warnings — the uncheckable
  channel — instead of returning `(None, None)` silently.
- `ve validate` output states how many symbol anchors it did not check
  (it verifies file parts only), so a clean single-tree run is never
  mistaken for symbol coverage.
- UNCHECKED never gates: no new errors, no new nonzero exits. Honest
  reporting only — no new resolution logic anywhere.
- Full test suite passes (baseline 4841); `uv run ve validate` on this
  repository still exits 0.