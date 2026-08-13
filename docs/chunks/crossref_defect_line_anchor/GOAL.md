---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/workspace_validation.py
- tests/test_workspace_validation.py
code_references:
- ref: src/workspace_validation.py#_find_field_entry_line
  implements: "Field-scoped line anchoring: first occurrence within the owning frontmatter field's YAML block, with whole-document fallback"
- ref: src/workspace_validation.py#_Validator::check_code_references
  implements: "All three finding sites (missing target, absent symbol, unverified qualified ref) anchor on the owning field's entry"
- ref: tests/test_workspace_validation.py#test_code_references_defect_anchors_past_an_identical_code_paths_entry
  implements: "Regression coverage: a path in both fields yields two defects anchored on their own entries"
- ref: tests/test_workspace_validation.py#test_zero_indent_list_style_anchors_correctly
  implements: "Zero-indent YAML list-item style anchors correctly and prose decoys attract nothing"
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

Workspace validation anchors every frontmatter finding on the offending entry itself: `check_code_references` reports a `line` located inside the frontmatter field that owns the entry (`code_paths` findings on the `code_paths` entry, `code_references` findings on the `- ref:` line), not the first textual occurrence of the path anywhere in GOAL.md. This keeps the fix loops (/validate-fix and /workspace-validate-fix) honest — a loop that trusts `line` edits the entry that is actually broken, rather than editing the code_paths twin, watching the anchor move, and reporting progress while the defect count holds (field report: a whole-document anchor cost a full validate pass on a 4000-file workspace). Frontmatter shapes the field scanner cannot follow degrade to the whole-document first occurrence rather than losing the line.

## Success Criteria

- Every finding produced by `check_code_references` in
  `src/workspace_validation.py` — the missing-target defect, the
  symbol-absence defect, and the unverified qualified-reference disposition —
  reports a `line` that lands inside the frontmatter field that owns the
  offending entry (`code_paths` findings anchor on the `code_paths` entry,
  `code_references` findings on the `- ref:` entry).
- The regression case is covered by a test: a path listed in both
  `code_paths` and `code_references`, where both are broken, yields two
  defects with distinct lines, each pointing at its own field's entry.
- Both YAML list-item styles used in the wild (zero-indent `- ref:` as `ve`
  emits, and indented `  - ref:` as hand-written frontmatter uses) anchor
  correctly.
- Frontmatter shapes the block scanner cannot parse degrade to the previous
  first-occurrence behavior, never to a lost line.
- Existing workspace-validation tests pass unchanged; `uv run ve validate` is
  clean.