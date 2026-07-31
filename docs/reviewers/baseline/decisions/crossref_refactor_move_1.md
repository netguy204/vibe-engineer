---
decision: FEEDBACK  # APPROVE | FEEDBACK | ESCALATE
summary: "Implementation is sound and evidence-rich, but symbol-less path entries with no successor are mislabeled NEVER_EXISTED even when the path demonstrably exists elsewhere in scope — the exact misleading-verdict class this chunk exists to kill."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve refactor move <old> <new>` rewrites every chunk frontmatter reference

- **Status**: satisfied
- **Evidence**: src/refactor_move.py#collect_references walks chunk GOAL.md
  code_paths + code_references and subsystem OVERVIEW.md code_references;
  HISTORICAL/SUPERSEDED skipped (_REWRITABLE_CHUNK_STATUSES); tests
  test_file_rename_rewrites_code_paths_and_references,
  test_split_rewrites_subsystem_overview_references,
  test_historical_chunks_are_left_as_archaeology.

### Criterion 2: Every rewrite carries reviewable evidence in the report: git rename/deletion

- **Status**: satisfied
- **Evidence**: gather_git_evidence (rename records + deletion sha) attached
  to every decision's evidence lines; AST verification lines per rewrite;
  test_file_rename_report_carries_git_and_ast_evidence,
  test_split_deletion_sha_is_reported_as_evidence,
  test_move_without_git_history_is_reported_operator_asserted (honesty when
  history is silent).

### Criterion 3: Basename-based inference never fires unless the candidate's immediate parent

- **Status**: satisfied
- **Evidence**: _guarded_basename_candidates requires parent.name match;
  regression tests test_basename_inference_requires_matching_parent_directory
  (the requirements.txt near-miss) and
  test_basename_inference_accepts_matching_parent_directory.

### Criterion 4: Module→package splits resolve each symbol anchor to the one file in the new

- **Status**: satisfied
- **Evidence**: find_symbol_definers + _defined_names (AST incl. assignment
  targets); unique definer rewrites, multiple → AMBIGUOUS with implements
  prose and candidates; tests
  test_split_resolves_symbols_to_their_unique_definer,
  test_ambiguous_symbol_surfaces_implements_prose_and_candidates.

### Criterion 5: A symbol with no successor anywhere in scope is reported as the distinct

- **Status**: gap (for the symbol-less path variant — see Feedback Items)
- **Evidence**: For symbol anchors the ladder is correct
  (test_symbol_absent_everywhere_is_never_existed_with_absence_basis,
  test_symbol_found_elsewhere_in_scope_is_ambiguous_not_never_existed). But
  a symbol-less entry (code_paths / file-only ref) with no successor under
  `new` is declared NEVER_EXISTED after only a *text* search on its
  basename — even when a file of that name exists elsewhere in scope as a
  path. That mislabels "moved outside the declared destination" as "never
  existed", the same class of misleading verdict the goal targets.

### Criterion 6: `--dry-run` previews without writing; `--format json` emits the full

- **Status**: satisfied
- **Evidence**: test_dry_run_writes_nothing, test_json_report_shape;
  applied flag in the report.

### Criterion 7: Real-world acceptance: running the tool for the `src/models.py` →

- **Status**: satisfied
- **Evidence**: models_move_report.json chunk artifact: 21 rewritten with
  AST + deletion-sha evidence, 4 Scratchpad* symbols NEVER_EXISTED (left
  in place, ledger pointer), 0 ambiguous; subsystem validate errors
  62 → 41; src/ve.py case refused by the old-still-exists guard
  (test_refuses_when_old_still_exists).

## Feedback Items

- id: issue-pathless-never-existed
  location: src/refactor_move.py#resolve_entry (the `entry.symbol_part is
    None and successor is None` branch)
  concern: A symbol-less entry with no successor under `new` gets
    NEVER_EXISTED backed by a whole-word *text* search on its basename. If
    the file exists elsewhere in scope as a *path* (e.g. the
    requirements.txt that lives in a different package), the honest verdict
    is AMBIGUOUS with those path candidates for the operator — claiming
    never-existed when the path exists elsewhere sends the operator toward
    a drop when a repoint may be correct.
  suggestion: Before declaring NEVER_EXISTED for a symbol-less entry, run a
    path-query absence search (ExistenceQuery with path_query set to the
    basename) and surface path/basename matches as AMBIGUOUS candidates;
    only an empty path search earns NEVER_EXISTED. Add a regression test
    where the same-basename file exists outside `new`.
  severity: functional
  confidence: high

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
