

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Two coupled affordances, built on machinery the reference_integrity narrative
already established:

**(a) Evidence-of-absence query — `ve exists NAME`.** A top-level command
(peer of `ve validate`) backed by a new `src/absence.py` module. The question
it answers is exactly the GOAL's: "does this name (path or symbol) exist
anywhere I can see?" Visibility is resolved the same way the workspace
validator resolves it: if a `.ve-workspace.yaml` manifest is found upward from
`--dir`, the scan scope is the workspace root plus every registered member
(same union-and-dedupe as `workspace_validation.enumerate_workspace_files`);
otherwise the scope falls back to the nearest enclosing VE tree, and failing
that the directory itself. The report always states the scope and the file
counts — that is what turns "not found" from silence into evidence.

Query parsing mirrors the reference grammar already in use
(`file#symbol::path` in `code_references`):

- `a/b.py#Sym` → path query `a/b.py` + symbol query `Sym` (last `::` part)
- contains `/` or a dot in the last component → path query only
- a bare identifier → symbol query *and* name-equality search (so artifact
  directory names and module directories are findable)
- anything else → literal content search

Path matching reports two distinct classes because they answer different
operator questions: **path matches** (relative path equals or ends with the
query — "it still exists") and **basename matches** (same final name at a
different path — "it moved"). That distinction is precisely what turned 18
lost-or-moved judgment calls into one decision in the field. Path matching
must see *all* files, not just source extensions (field cases were
`requirements.txt` and `Dockerfile`), so a new `enumerate_all_files` helper
lands in `src/source_files.py` beside `enumerate_source_files`, reusing the
same git-aware enumeration with the extension filter removed. Symbol/content
matching scans source files with the same conservative whole-word semantics as
`workspace_validation._symbol_is_absent`, so `ve exists` and the validator
never disagree about what "present" means.

Exit code is grep-shaped: 0 when anything matched, 1 when absent — so skills
and scripts can branch on it. `--format json` emits the full report for the
fix-loop skills.

**(b) Operator-authorized deletion disposition — `ve deletion record`/`list`.**
A new `src/deletions.py` module owning an append-only ledger at
`docs/trunk/DELETIONS.md` (created on first record — command-created, per the
"never manually create artifact files" rule), modeled on the friction ledger
(`src/friction.py`) but simpler: no themes, just numbered entries. Each grant
records the reference as written, the location it was deleted from, who
authorized it, why, and optional absence evidence (typically the `ve exists`
summary line). The validators do not read the ledger — once the reference is
deleted there is nothing left to validate; the ledger is the audit trail that
makes the deletion reviewable in the same diff that removes the reference.

**Skill vocabulary.** Both fix-loop skills gain the disposition:

- `workspace-validate-fix.md.jinja2`: the "Never delete a reference" invariant
  keeps its sentence verbatim (a contract test asserts it) and gains the one
  blessed exception: an explicit operator grant, recorded with
  `ve deletion record` *before* the reference is removed. Escalation guidance
  for `unresolvable-bare`/`missing-target` tells the agent to attach
  `ve exists` output as evidence, and the report format gains an
  "Authorized deletions" section distinct from Fixed and Escalations.
- `validate-fix.md.jinja2`: the classification table gains the third
  disposition (neither auto-fixable nor merely unfixable) with the same
  evidence → operator grant → record → delete → report sequence.

Both templates get `Bash(ve exists:*)` and `Bash(ve deletion:*)` in
allowed-tools, and `uv run ve plugin render` regenerates
`skills/*/SKILL.md`.

Constraints honored: DEC-005 (no git operations prescribed — the commands
write files only), DEC-002 (git not assumed — file enumeration falls back to
rglob), TDD per docs/trunk/TESTING_PHILOSOPHY.md (behavioral tests first for
the query semantics and ledger append).

## Sequence

### Step 1: Failing tests for the existence query

New `tests/test_absence_evidence.py`. Using `conftest.make_ve_tree` /
`make_workspace` fixtures (as `tests/test_workspace_validation.py` does),
assert:

- a file present in a member tree is reported as a path match; exit 0
- a file that exists nowhere reports absence, names the scan scope
  (workspace root + members) and a nonzero files-scanned count; exit 1
- a moved file (same basename, different directory) is reported as a
  basename match, distinct from path matches
- a symbol defined in a source file is found with `file:line`; a symbol
  appearing nowhere is absent (whole-word: `foo_bar` does not match `foo`)
- `file#symbol` queries check both parts
- directory names match identifier queries (e.g. an artifact directory)
- no manifest → falls back to the enclosing tree and says so
- `--format json` carries `query`, `found`, match lists, and `scope`/counts

### Step 2: Implement `src/absence.py` and `enumerate_all_files`

- `src/source_files.py`: add `enumerate_all_files(project_dir)` — same
  git-ls-files-or-rglob strategy as `enumerate_source_files`, no extension
  filter (still excludes `FALLBACK_EXCLUDE_DIRS` in the fallback).
- `src/absence.py`: `ExistenceQuery.parse(raw)`, `ExistenceReport`
  (dataclass with `found`, `path_matches`, `basename_matches`,
  `symbol_matches`, `scope`, counts, `to_dict()`), and
  `search_existence(roots, query)`. Directory matching walks the roots for
  dir-name/dir-path hits; content matching reuses the whole-word regex
  semantics of `_symbol_is_absent`.

### Step 3: CLI — `ve exists`

New `src/cli/exists_cmd.py`: `exists` command with `NAME` argument,
`--dir` (default `.`), `--format text|json`. Scope resolution:
`workspace.find_workspace_root` upward, else `project.find_enclosing_tree`,
else the directory itself. Text output prints match sections (capped per
section with a "… and N more" line; JSON is complete), then the scope line:
`Scanned N files across M trees rooted at <root>`. Register in
`src/cli/__init__.py` above the `install_tree_discovery` call.

### Step 4: Failing tests for the deletion ledger

In the same test module (or `tests/test_deletion_ledger.py` if it grows):

- `ve deletion record` with `--reference`, `--location`, `--by`, `--reason`
  (and optional `--evidence`) creates `docs/trunk/DELETIONS.md` on first use
  with a guidance header, appends `D001`, and echoes the id
- a second record appends `D002` without disturbing `D001`
- `ve deletion list` shows both; `--format json` round-trips every field
- recording outside a VE tree fails with an actionable error

### Step 5: Implement `src/deletions.py` and `ve deletion` CLI

- `DeletionLedger(project_dir)`: `record(...) -> str` (creates the file if
  missing, computes next `D###` id, appends the entry), `entries() ->
  list[DeletionGrant]` (regex parse, mirroring `friction.parse_entries`'
  style). Entry format:

  ```
  ### D001: 2026-07-31 — `docs/chunks/foo` deleted from `src/bar.py:12`

  - **Authorized by**: <operator>
  - **Reason**: <why the deletion is correct>
  - **Evidence**: <e.g. `ve exists` summary — absent across 4212 files>
  ```

- `src/cli/deletion.py`: `deletion` group with `record` and `list`,
  `--project-dir` option consistent with other groups so tree discovery
  applies. Register in `src/cli/__init__.py`.

### Step 6: Skill templates and re-render

- Edit `src/templates/plugin/skills/workspace-validate-fix.md.jinja2` and
  `src/templates/plugin/skills/validate-fix.md.jinja2` as described in
  Approach. Keep the literal sentence "Never delete a reference." intact —
  `tests/test_workspace_validate_fix_skill.py::test_document_states_the_three_invariants`
  pins it.
- Add contract assertions to `tests/test_absence_evidence.py`: both rendered
  skills mention `ve exists`, `ve deletion record`, and an
  "Authorized deletions" report section; the workspace skill still states all
  three invariants.
- Run `uv run ve plugin render`; commit the regenerated
  `skills/validate-fix/SKILL.md` and `skills/workspace-validate-fix/SKILL.md`.

### Step 7: Document the ledger in ARTIFACTS.md

Add a short "Deletion grants" note to `src/templates/trunk/ARTIFACTS.md.jinja2`
(near the friction-log section): what `docs/trunk/DELETIONS.md` is, that it is
created by `ve deletion record`, and that reference deletion without a
recorded grant is out of vocabulary. Apply the same edit to the rendered
`docs/trunk/ARTIFACTS.md` (this repo's instance).

### Step 8: Backreferences, validation, full test run

- Add `# Chunk: docs/chunks/crossref_absence_evidence` backreferences to the
  new modules and CLI commands.
- Update this chunk's GOAL.md `code_references`.
- `uv run pytest tests/` and `uv run ve validate` both clean.

## Dependencies

None on other narrative chunks — `depends_on: []` is deliberate; this chunk
touches no validator internals the parallel chunks are editing.
`crossref_refactor_move` (a later wave) consumes this chunk's absence query
for its never-existed disposition, so the JSON report shape is a contract.

## Risks and Open Questions

- **Scan cost on large workspaces.** The query reads every source file once
  for symbol search. That is the same cost profile as one validator pass,
  which the 4000-file field workspace already tolerates; no index is built.
- **Name collisions in text output.** A short identifier can match thousands
  of lines; text output caps each section and points at `--format json`.
- **Ledger placement in workspaces.** A grant is recorded in the tree named
  by `--project-dir` (the tree that governed the deleted reference). The
  command does not guess across trees; the skill text says to record in the
  governing tree.
- **`ve exists` vs future `ve refactor move`.** The move tool (later chunk)
  will want richer git-history evidence; this chunk deliberately scopes
  visibility to the current working copy — "anywhere I can see" now, not
  "anywhere that ever existed".

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
