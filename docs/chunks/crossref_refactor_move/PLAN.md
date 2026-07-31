

# Implementation Plan

## Approach

Build a new module `src/refactor_move.py` (evidence-backed reference
rewriting) and a new CLI group `ve refactor` with a `move` subcommand in
`src/cli/refactor.py`. The tool answers one operator declaration — "the code
at `<old>` now lives at `<new>`" — by finding every frontmatter reference
naming the old path, deciding each entry's disposition with reviewable
evidence, and rewriting only the unambiguous ones.

Build on existing machinery rather than inventing parallel semantics:

- **Symbol verification**: `symbols.extract_symbols` (AST) and the semantics
  of `symbols.check_reference_target` — the same "absent" the validators use.
- **Never-existed disposition**: `absence.resolve_scope` /
  `absence.search_existence` from `crossref_absence_evidence` (declared
  dependency). "No successor found" is reported with the absence report's
  scope + counts as its basis, never as "renamed or removed".
- **Reference enumeration**: `Chunks` / `Subsystems` frontmatter parsing, the
  same models `IntegrityValidator._validate_chunk_file_paths` and
  `Subsystems.validate_code_references` check.
- **Git evidence**: `git log --follow --name-status` (rename shas) and
  `git log --diff-filter=D` (deletion sha), subprocess style mirroring
  `src/git_utils.py`.

Scope decisions (aligned with the narrative's acceptance context):

- The rewrite covers chunk GOAL.md `code_paths` + `code_references` file
  parts (the GOAL's core) **and** subsystem OVERVIEW.md `code_references`
  file parts — the narrative's real-world acceptance suite (62 stale
  subsystem refs on this repo) lives in subsystem frontmatter, and both are
  checked by the same validators the tool exists to satisfy.
- HISTORICAL and SUPERSEDED chunks are never rewritten: their stale paths are
  archaeology, and `_validate_chunk_file_paths` deliberately skips them.
- Project-qualified refs (`org/repo::path#sym`) are skipped (cross-repo
  addressing is out of scope, matching the validators).
- The tool never deletes a reference. NEVER_EXISTED and AMBIGUOUS entries are
  reported for operator disposition (reconstruct, hand-fix, or record via
  `ve deletion record`).

### Disposition model

For each matching entry, exactly one of:

- **REWRITTEN** — an unambiguous successor was found and verified; the entry
  is rewritten and the decision carries evidence lines (git shas, AST
  verification, or parent-dir-guarded path mapping).
- **AMBIGUOUS** — several candidates qualify (or a symbol exists elsewhere
  but not uniquely under the new path). The entry is left unchanged; the
  report surfaces the entry's `implements:` prose alongside the candidates,
  because prose out-performs name similarity for module→package splits.
- **NEVER_EXISTED** — the symbol has no match anywhere in the visibility
  scope (absence report attached). Reconstruct-or-drop; the report says so
  explicitly and points at `ve deletion record` for the drop path.

### Resolution cases

Given `old` (must be gone from disk) and `new` (must exist):

1. **file → file** (`new` is a file, entry file part == `old`): successor
   file is `new`. Symbol anchors are verified against `new` via AST, falling
   back to whole-word occurrence for constants (mirroring
   `check_reference_target`); a symbol absent from `new` escalates to the
   scope-wide absence search → AMBIGUOUS (found elsewhere, candidates
   listed) or NEVER_EXISTED (found nowhere).
2. **directory → directory** (entry file part == `old` or starts with
   `old/`): map `old/rest` → `new/rest`. If the mapped path does not exist,
   basename inference may run under `new` — but only accepts a candidate
   whose basename **and immediate parent directory name** both match the
   original's (the `requirements.txt` near-miss guard). Zero or multiple
   guarded candidates → escalate as in case 1.
3. **module → package split** (`old` is a `.py` path, `new` is a
   directory): a symbol anchor resolves by AST-scanning `new/**/*.py` for
   files defining the full symbol path; exactly one definer → REWRITTEN to
   that file, several → AMBIGUOUS (implements prose + candidates), none →
   absence-search escalation. A symbol-less entry (plain `code_paths` entry
   or file-only ref) rewrites to the `new` directory itself — directories
   are legitimate reference targets per `crossref_workspace_parity`.

Git evidence is gathered once per invocation: rename records
(`R###  old  new`) from `git log --follow --name-status -- <new>` (prefix
matching for directory moves) and the deletion sha of `old` from
`git log --diff-filter=D -n1 -- <old>`. When neither exists the move is
reported as "operator-asserted (no git evidence)" — the tool still proceeds
on verifiable on-disk facts, but the report is honest about the weaker basis.

### Guardrails

- Error out if `old` still exists on disk (that is not a completed move — the
  `src/ve.py` field case) or if `new` does not exist.
- Rewrites edit only the YAML frontmatter block, and only lines whose scalar
  value is exactly the old value (`- <old...>` list items and `ref:` values,
  quoted or not) — prose bodies are never touched.
- `--dry-run` produces the full report without writing.
- `--format json` emits the machine-readable report (dispositions, evidence,
  candidates, absence bases) for fix-loop consumption.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): this chunk USES the
  chunk/subsystem artifact managers (`Chunks`, `Subsystems`) to enumerate and
  parse frontmatter. New code follows their access patterns; no deviations
  introduced.

## Sequence

### Step 1: Core data model and reference collection

In `src/refactor_move.py`: dataclasses `RefEntry` (artifact file, artifact
kind/status, field name, raw value, file part, symbol part, `implements`
prose or None), `MoveDecision` (entry, disposition, new value, evidence
lines, candidates, absence basis), `GitMoveEvidence`, `MoveReport` (with
`to_dict()`). `collect_references(project_dir, old)` walks all chunks
(skipping HISTORICAL/SUPERSEDED) and all subsystems, returning entries whose
file part equals `old` or lies under `old/`, skipping project-qualified refs.

### Step 2: Git evidence

`gather_git_evidence(project_dir, old, new)` shells out to git: parses
`R`-status records from `git log --follow --name-status --format=%H -- <new>`
and the deletion sha from `git log --diff-filter=D --format=%H -n 1 -- <old>`.
Tolerates non-repo directories (evidence empty, not an error).

### Step 3: Successor resolution

`resolve_entry(project_dir, entry, old, new, scope)` implementing the three
cases and the escalation ladder above. Helper `find_symbol_definers(root,
symbol_path)` AST-scans Python files under a directory; helper
`_guarded_basename_candidates` enforces the parent-directory guard.
Absence escalation reuses `absence.search_existence` on the symbol leaf.

### Step 4: Frontmatter rewriting

`apply_rewrites(decisions)` groups REWRITTEN decisions by artifact file and
performs line-precise replacement inside the frontmatter block only:
a line whose stripped form is `- <old_value>` / `ref: <old_value>` (allowing
quotes) becomes the same shape with the new value. Refuses (raises) if an
expected value is not found, so a drifted file can't be half-rewritten
silently.

### Step 5: CLI

`src/cli/refactor.py`: `ve refactor` group + `move` command
(`OLD NEW --project-dir --dry-run --format {text,json}`). Human output groups
by disposition, prints evidence lines per rewrite, prints `implements:`
prose + candidates for AMBIGUOUS, absence basis for NEVER_EXISTED, and a
summary. Exit 0 when nothing failed structurally (ambiguous/never-existed
entries are report content, not command failure). Register in
`src/cli/__init__.py` above the tree-discovery install.

### Step 6: Tests

`tests/test_refactor_move.py` with tmp git repos (fixtures create a VE-ish
tree with `docs/chunks/*/GOAL.md`, `docs/subsystems/*/OVERVIEW.md`, real
`git mv` history):

- file→file rename: chunk code_paths + code_references rewritten; rename sha
  present in evidence; symbol verified.
- directory move: prefix mapping, including a file whose mapped path is
  missing but recoverable via the parent-dir-guarded basename search.
- parent-dir guard regression: same basename in a *different* parent under
  `new` is NOT matched (requirements.txt near-miss).
- module→package split: symbol resolved to its unique definer; symbol in two
  files → AMBIGUOUS with implements prose; symbol nowhere → NEVER_EXISTED
  with absence basis.
- old still on disk → command errors; new missing → command errors.
- HISTORICAL chunk untouched; project-qualified ref untouched.
- subsystem OVERVIEW code_references rewritten.
- `--dry-run` writes nothing; JSON report shape stable.

### Step 7: Real-world acceptance run

Run `uv run ve refactor move src/models.py src/models` against this repo:
it must repair the `src/models.py` stale subsystem code_references (20 of
the 62) with per-entry AST + git evidence. Save the JSON report as a chunk
artifact (`docs/chunks/crossref_refactor_move/models_move_report.json`).
Verify with `uv run ve subsystem validate` (workflow_artifacts error count
drops by the repaired entries) and `uv run ve validate` stays clean. Leave
`src/scratchpad.py` / `src/sync.py` (deletions — ledger territory) and
`src/ve.py` (old still exists — tool correctly refuses) defects in place and
report them.

## Dependencies

- `crossref_absence_evidence` (ACTIVE): `absence.resolve_scope` /
  `search_existence` for the NEVER_EXISTED basis; `ve deletion record` as the
  pointed-to drop path. Already on main.

## Risks and Open Questions

- `git log --follow` rename detection is heuristic (similarity-based); for a
  module→package split git usually reports a delete + adds, not renames. The
  evidence model treats deletion-sha-only as valid evidence for splits.
- Frontmatter line rewriting assumes block-style YAML lists (what `ve` tools
  emit). Flow-style lists would not match; the rewriter raises rather than
  silently skipping, so drift is loud.
- AST symbol scanning covers Python only; symbol anchors on non-Python
  successors fall back to whole-word text presence (same honesty level as
  `check_reference_target`).

## Deviations

No significant deviations from the planned approach. Notes from the
real-world acceptance run (Step 7):

- 25 references named `src/models.py` (the plan estimated ~20 from the
  validate-error counts; the extra entries were symbol-check errors on the
  same old path, plus one ref in a passing subsystem). Outcome: 21 rewritten
  with per-entry AST + git-deletion evidence
  (`models_move_report.json`), 4 `Scratchpad*` symbols correctly reported
  NEVER_EXISTED (that code was deliberately removed, not moved — deletion-
  ledger territory, left for the operator), 0 ambiguous.
- Subsystem validate error count dropped 62 → 41. The 41 remaining are:
  `src/scratchpad.py` / `src/sync.py` refs (deleted code, ledger territory),
  `src/ve.py` symbol misses (the old file still exists — a symbol-level
  split the tool refuses by design), and the never-existed Scratchpad
  symbols above. None were bulk-fixed without evidence, per the narrative's
  acceptance constraint.
- Review feedback (iteration 1) tightened the symbol-less ladder: a path
  entry with no successor under `new` now runs a *path* absence query on its
  basename — path matches elsewhere in scope surface as AMBIGUOUS candidates
  (the file may have moved outside the declared destination) and only an
  empty path search earns NEVER_EXISTED. The original implementation used a
  text search and could mislabel a moved file as never-existed.
- `_defined_names` extends AST extraction with module/class-level assignment
  targets so constants (`VALID_STATUS_TRANSITIONS` etc.) resolve to their
  defining file instead of every importer — planned as a helper detail,
  proved essential: 4 of the 21 real repairs (the `VALID_*_TRANSITIONS`
  tables) were assignment-defined names.
