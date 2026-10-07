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
- src/templates/claude/AGENTS.md.jinja2
- tests/test_absence_evidence.py
- tests/test_template_system.py
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
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: "Managed-block section stating the three tiers for removing a reference"
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

The system exposes an evidence-of-absence affordance and an operator-authorized deletion disposition. (a) `ve exists <name>` answers "does this name (path or symbol) exist anywhere I can see" — across the whole workspace when a manifest governs, else the nearest enclosing VE tree — reporting still-there, moved (same name elsewhere), and symbol matches, and stating the scanned scope so absence is a fact rather than silence; field experience: an absence search turned 18 lost-or-moved judgment calls into one operator decision backed by fact. (b) Removing a reference follows three tiers, stated in the managed AGENTS.md block, both validate-fix skills, ARTIFACTS.md, and the ledger header. Tier 1, an ordinary edit with no grant and no escalation: the author of a diff that removes or moves code updates the references to that code in the same diff while the intent they recorded survives, by retargeting a reference to the code that now carries the intent, dropping it if another reference already covers that intent, or dropping it when the intent no longer belongs to any chunk; the PR reviewer checks it in the diff. Tier 2, operator sign-off plus a ledger entry: removing the last reference that carries a chunk's intent abandons that intent, and this includes a diff that deletes the code carrying a chunk's whole intent, where sign-off wins over tier 1. Tier 3, fix loops: for a reference to code deleted earlier, outside the current diff, `ve exists` supplies the evidence, a same-name match elsewhere means the target moved and is retargeted, and otherwise the case goes to the operator and the grant is recorded in `docs/trunk/DELETIONS.md` via `ve deletion record` before the reference is removed, so the grant lands in the same diff and a reviewer can see it. "Never delete a reference just to make the validator pass" holds in every tier. Together these make "reference to deliberately deleted code" a decidable, auditable case.

## Success Criteria

- `ve exists NAME` answers whether a path or symbol exists anywhere in the
  visible scope: the whole workspace (root plus every registered member) when
  a `.ve-workspace.yaml` manifest is found upward, else the nearest enclosing
  VE tree. Output always states the scope and file counts, so absence is
  evidence backed by fact rather than silence.
- A moved file is distinguishable from a deleted one: exact path matches and
  same-basename-elsewhere matches are reported as distinct classes.
- Symbol presence uses the same conservative semantics as the workspace
  validator's `_symbol_is_absent` — whole-word occurrence, with Python
  import/`__all__`-only mentions classified as re-export evidence rather
  than presence (see docs/chunks/crossref_reexport_absence) — so the query
  and the validator never disagree about what "present" means.
- Exit code is scriptable: 0 when anything matched, 1 when absent;
  `--format json` emits the full machine-readable report the fix-loop skills
  consume.
- `ve deletion record` appends an operator-attributed grant (reference,
  location, authorized-by, reason, optional absence evidence) to
  `docs/trunk/DELETIONS.md`, creating the ledger on first use; `ve deletion
  list` shows grants, with `--format json`. The grant lands in the same diff
  that removes the reference, so a reviewer can see it.
- Both validate-fix skills name the authorized-deletion disposition: in a
  fix loop, deleting a reference to code removed outside the current diff is
  permitted only with an explicit operator grant recorded via
  `ve deletion record`, reported under an "Authorized deletions" section
  distinct from fixes and escalations. The workspace skill's "Never delete a
  reference." invariant sentence survives verbatim (contract-tested).
- The managed AGENTS.md block (single-tree and workspace renders), both
  validate-fix skills, ARTIFACTS.md, and the ledger header state the three
  tiers: tier 1 lets the author of a diff update references whose intent
  survives with no grant and no escalation; tier 2 requires operator sign-off
  and a ledger entry when a removal abandons a chunk's intent, including when
  the same diff deletes the code carrying a chunk's whole intent; tier 3 is the
  fix-loop procedure above. Each states "Never delete a reference just to make
  the validator pass."
- No git operations are prescribed by either command (DEC-005).
- Tests cover the query (found / absent / moved / symbol / no-manifest
  fallback / JSON shape), the ledger (create, append, list, error outside a
  tree), and the skill contract; `uv run pytest tests/` and
  `uv run ve validate` are clean.

