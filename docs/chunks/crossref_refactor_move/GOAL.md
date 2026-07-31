---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/refactor_move.py
- src/cli/refactor.py
- src/cli/__init__.py
- tests/test_refactor_move.py
code_references:
- ref: src/refactor_move.py#execute_move
  implements: The move operation end to end (guards, evidence, resolution, rewrite)
- ref: src/refactor_move.py#collect_references
  implements: Enumerating chunk/subsystem frontmatter entries naming the old path,
    skipping HISTORICAL archaeology and project-qualified refs
- ref: src/refactor_move.py#gather_git_evidence
  implements: Git rename/deletion shas as reviewable move evidence
- ref: src/refactor_move.py#resolve_entry
  implements: Per-entry disposition ladder (rewrite / ambiguous with implements prose
    / never-existed with absence basis)
- ref: src/refactor_move.py#_guarded_basename_candidates
  implements: The parent-directory guard on basename inference
- ref: src/refactor_move.py#_defined_names
  implements: AST symbol indexing extended with assignment targets so constants resolve
    to their defining file
- ref: src/refactor_move.py#find_symbol_definers
  implements: Module-to-package split symbol resolution
- ref: src/refactor_move.py#apply_rewrites
  implements: Frontmatter-scoped line-precise rewriting that never touches prose
- ref: src/refactor_move.py#MoveReport
  implements: The evidence report contract (JSON and human output)
- ref: src/cli/refactor.py#move
  implements: The `ve refactor move` CLI with --dry-run and --format json
- ref: src/cli/__init__.py
  implements: Registration of the `ve refactor` command group
- ref: tests/test_refactor_move.py
  implements: Regression coverage for the field-tested guards and dispositions
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on:
- crossref_absence_evidence
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
---
# Chunk Goal

## Minor Goal

`ve refactor move <old> <new>` rewrites every chunk frontmatter reference (code_paths, code_references file parts) — and every subsystem OVERVIEW code_reference — naming the old path, with field-tested guards baked in. Basename-based inference requires the immediate parent directory name to match (documented near-miss: a unique basename match resolving update-potential-savings/requirements.txt to a different package's requirements.txt); git rename detection (git log --follow, --diff-filter=D shas) is preferred as reviewable evidence over inference; each entry's implements: prose surfaces at every ambiguous decision point (it out-performs name similarity for module→package splits); and 'no successor found' is a distinct never-existed/reconstruct-or-drop disposition — 8 field refs named symbols that never existed in code, and an existence checker that says 'renamed or removed' sends the fixer hunting for a rename that does not exist. The tool never deletes a reference; drops route through the evidence-of-absence affordance and the operator deletion ledger (`ve deletion record`).

## Success Criteria

- `ve refactor move <old> <new>` rewrites every chunk frontmatter reference
  (`code_paths` entries and `code_references` file parts) and every subsystem
  OVERVIEW `code_references` file part that names `<old>`, in every
  intent-owning artifact (HISTORICAL/SUPERSEDED chunks are left as
  archaeology).
- Every rewrite carries reviewable evidence in the report: git rename/deletion
  SHAs (`git log --follow --name-status`, `--diff-filter=D`) when git history
  supports the move, and symbol-verification results (AST) for symbol anchors.
- Basename-based inference never fires unless the candidate's immediate parent
  directory name matches the original's (regression test encoding the
  `update-potential-savings/requirements.txt` near-miss).
- Module→package splits resolve each symbol anchor to the one file in the new
  package that defines it; when zero or several files qualify, the entry is
  reported AMBIGUOUS with its `implements:` prose and the candidate list, and
  is left unchanged.
- A symbol with no successor anywhere in scope is reported as the distinct
  NEVER_EXISTED (reconstruct-or-drop) disposition, backed by the
  evidence-of-absence report (`crossref_absence_evidence`), never as
  "renamed or removed".
- `--dry-run` previews without writing; `--format json` emits the full
  machine-readable report.
- Real-world acceptance: running the tool for the `src/models.py` →
  `src/models/` split repairs those stale subsystem code_references with
  per-entry evidence; deliberately-deleted (`src/scratchpad.py`) and
  still-existing-old (`src/ve.py`) cases are correctly refused/left for
  operator dispositions.

