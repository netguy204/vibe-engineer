---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/absence.py
- src/deletions.py
- src/source_files.py
- src/cli/exists_cmd.py
- src/cli/deletion.py
- src/cli/__init__.py
- src/templates/plugin/skills/validate-fix.md.jinja2
- src/templates/plugin/skills/workspace-validate-fix.md.jinja2
- skills/validate-fix/SKILL.md
- skills/workspace-validate-fix/SKILL.md
- src/templates/trunk/ARTIFACTS.md.jinja2
- docs/trunk/ARTIFACTS.md
- tests/test_absence_evidence.py
code_references:
- ref: src/absence.py#ExistenceQuery
  implements: "Query parsing: path, symbol, or file#symbol questions"
- ref: src/absence.py#resolve_scope
  implements: "Visibility scope: workspace, else enclosing tree, else directory"
- ref: src/absence.py#search_existence
  implements: "The search: path/basename/symbol match classes with scan counts"
- ref: src/cli/exists_cmd.py#exists
  implements: "ve exists CLI: text/JSON output, grep-shaped exit code"
- ref: src/deletions.py#DeletionLedger
  implements: "Append-only docs/trunk/DELETIONS.md grant ledger"
- ref: src/cli/deletion.py#record
  implements: "ve deletion record: writes the grant before the reference is removed"
- ref: src/cli/deletion.py#list_grants
  implements: "ve deletion list: text and JSON grant listing"
- ref: src/cli/__init__.py
  implements: "Registers ve exists and ve deletion in the CLI assembly"
- ref: src/source_files.py#enumerate_all_files
  implements: "All-files enumeration so path queries see non-source files"
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

The system exposes an evidence-of-absence affordance and an operator-authorized deletion disposition. (a) `ve exists <name>` answers "does this name (path or symbol) exist anywhere I can see" — across the whole workspace when a manifest governs, else the nearest enclosing VE tree — reporting still-there, moved (same name elsewhere), and symbol matches, and stating the scanned scope so absence is a fact rather than silence; field experience: an absence search turned 18 lost-or-moved judgment calls into one operator decision backed by fact. (b) The validate-fix skills' vocabulary keeps "never delete a reference" and carries a blessed third disposition that is neither fix nor silence: an operator-authorized deletion is recorded in `docs/trunk/DELETIONS.md` via `ve deletion record` before the reference is removed, so the grant lands in the same diff as the deletion and a reviewer can see it. Together these make "reference to deliberately deleted code" a decidable, auditable case.

## Success Criteria

- `ve exists NAME` answers whether a path or symbol exists anywhere in the
  visible scope: the whole workspace (root plus every registered member) when
  a `.ve-workspace.yaml` manifest is found upward, else the nearest enclosing
  VE tree. Output always states the scope and file counts, so absence is
  evidence backed by fact rather than silence.
- A moved file is distinguishable from a deleted one: exact path matches and
  same-basename-elsewhere matches are reported as distinct classes.
- Symbol presence uses the same conservative whole-word semantics as the
  workspace validator's `_symbol_is_absent`, so the query and the validator
  never disagree about what "present" means.
- Exit code is scriptable: 0 when anything matched, 1 when absent;
  `--format json` emits the full machine-readable report the fix-loop skills
  consume.
- `ve deletion record` appends an operator-attributed grant (reference,
  location, authorized-by, reason, optional absence evidence) to
  `docs/trunk/DELETIONS.md`, creating the ledger on first use; `ve deletion
  list` shows grants, with `--format json`. The grant lands in the same diff
  that removes the reference, so a reviewer can see it.
- Both validate-fix skills name the authorized-deletion disposition: deleting
  a reference is permitted only with an explicit operator grant recorded via
  `ve deletion record`, reported under an "Authorized deletions" section
  distinct from fixes and escalations. The workspace skill's "Never delete a
  reference." invariant sentence survives verbatim (contract-tested).
- No git operations are prescribed by either command (DEC-005).
- Tests cover the query (found / absent / moved / symbol / no-manifest
  fallback / JSON shape), the ledger (create, append, list, error outside a
  tree), and the skill contract; `uv run pytest tests/` and
  `uv run ve validate` are clean.

