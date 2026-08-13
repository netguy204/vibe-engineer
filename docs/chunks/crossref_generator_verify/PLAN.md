

# Implementation Plan

## Approach

The chunk closes two generator-side holes that manufacture the reference debt
the validator later finds:

1. **Subsystem discovery** writes `code_references` into subsystem OVERVIEW
   frontmatter with no verification affordance — `ve subsystem validate`
   today checks only chunk refs, so an invented symbol name (field case:
   `OriginationSimulator`) lands silently.
2. **Chunk completion** treats a code_references entry naming a nonexistent
   file/symbol as a *warning* (`_validate_symbol_exists_with_context` in
   src/chunk_validation.py), and `ve chunk complete` performs no validation
   at all before flipping status to ACTIVE — so a ref can be stale at birth
   and still land.

Strategy: extract one shared reference-existence check (building on the
existing `symbols.extract_symbols` / `parse_reference` machinery), route both
chunk validation and a new subsystem code_references validation through it,
promote provable absence from warning to error in chunk validation, gate
`ve chunk complete` on it, and amend the two skill templates
(subsystem-discover, chunk-complete) so the agent flows verify what they
write. This mirrors the direction set by docs/chunks/crossref_rename_integrity
(stale declared paths fail loudly for chunks that own intent) and stays
consistent with the honest-reporting principle of the reference_integrity
narrative: absence is an error, *uncheckable* is a surfaced warning, never a
silent pass.

Scope guards (siblings own these): re-export/`__all__` absence semantics
(crossref_reexport_absence), non-identifier anchors (crossref_unchecked_anchors),
glob expansion (crossref_glob_refs), and workspace-mode parity
(crossref_workspace_parity) are explicitly out of scope. The shared check
keeps today's whole-file `extract_symbols` semantics.

TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests for each new
disposition first, then implement.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): this chunk IMPLEMENTS part
  of the artifact lifecycle — validation of artifact-declared code references
  at completion/validation time. `src/symbols.py`, `src/subsystems.py`, and
  the CLI command modules already carry this subsystem's backreferences.
- **docs/subsystems/template_system** (STABLE): this chunk USES the template
  system. Hard invariant respected: edit `src/templates/plugin/skills/*.jinja2`
  sources, re-render with `uv run ve plugin render`, never edit
  `skills/*/SKILL.md` renders directly.

## Sequence

### Step 1: Shared reference-existence check in src/symbols.py

Add a public function:

```python
def check_reference_target(project_dir: Path, ref: str) -> tuple[str | None, str | None]:
    """Check a local (non-project-qualified) symbolic reference against a project.

    Returns (error, warning):
    - error:   file does not exist, or symbol not found in a parseable Python file
    - warning: Python file exists but could not be parsed (uncheckable)
    - (None, None): verified, or not symbol-checkable (non-Python file / no symbol)
    """
```

Behavior (preserving today's semantics from
`chunk_validation._validate_symbol_exists_with_context`, only reclassified):
- Parse via `qualify_ref(ref, ".")` + `parse_reference`.
- Missing file → error `"File not found: {file_path} (ref: {ref})"`.
- No symbol part → verified after file check.
- `extract_symbols` empty on a `.py` file → warning
  `"Could not extract symbols from {file_path} (ref: {ref})"`.
- Symbol not in extracted set (Python) → error
  `"Symbol not found: {symbol_path} in {file_path} (ref: {ref})"`.
- Non-Python files with a symbol part → (None, None) (unchanged; honest
  UNCHECKED reporting belongs to crossref_unchecked_anchors).

Backreference: `# Chunk: docs/chunks/crossref_generator_verify`.

Tests first in tests/test_symbols.py: one test per disposition (missing file,
missing symbol, valid symbol, file-only ref, non-Python symbol anchor,
unparseable Python file).

### Step 2: Promote absence to error in chunk validation

In src/chunk_validation.py:
- Change `_validate_symbol_exists_with_context` to return
  `tuple[list[str], list[str]]` (errors, warnings). Local branch and the
  resolved-project cross-project branch delegate to `check_reference_target`
  (passing the resolved project dir; keep the `in project {ref}` phrasing for
  cross-project messages). Keep as warnings: "Skipped cross-project reference
  (no task context)" and "Could not resolve project".
- Delete the now-unused private `_validate_symbol_exists` (no callers outside
  this module) and update the module docstring.
- In `validate_chunk_complete`, extend `errors` with the returned errors and
  `warnings` with the warnings.

Add a completion-gate helper used by Step 3:

```python
def validate_chunk_references_exist(
    chunks: Chunks, chunk_name: str, task_dir: pathlib.Path | None = None,
) -> tuple[list[str], list[str]]:
```

which checks *only existence* of declared entries (empty lists pass):
- each `code_paths` entry exists (`.exists()`, directories allowed — parity
  with `IntegrityValidator._validate_chunk_file_paths`);
- each `code_references` entry passes
  `_validate_symbol_exists_with_context` (errors block, warnings pass
  through).

Tests first: update tests/test_chunk_validate.py
`TestSymbolicReferenceValidation` — nonexistent symbol/file now exit 1 with
the message on stderr; valid refs unchanged; add an unparseable-Python case
asserting exit 0 + warning.

### Step 3: Gate `ve chunk complete` on reference existence

In src/cli/chunk.py:
- `complete_chunk` (single-repo path): after resolving `chunk_name`, call
  `chunks.validate_chunk_references_exist(...)` (expose a thin wrapper on
  `Chunks` following the existing wrapper pattern, or call the
  chunk_validation function directly with the `Chunks` instance — follow the
  existing routing style used by `validate_chunk_complete`). On errors: print
  each, then guidance:
  "Cannot complete: code references name targets that do not exist. Fix the
  reference or the code (a chunk cannot land pointing at code that does not
  exist); if the target was deliberately deleted, escalate to the operator."
  Exit 1 without touching the frontmatter.
- `_complete_task_chunk`: same gate against the external repo's `Chunks`
  with `task_dir` supplied, before `update_frontmatter_field`.

Tests first (tests/test_chunk_scratchpad_cli.py or a new
tests/test_chunk_complete_gate.py):
- complete succeeds when code_references point at an existing file+symbol;
- complete exits 1 and leaves status IMPLEMENTING when a ref names a missing
  file; same for a missing symbol;
- complete still succeeds with empty code_references (existing minimal-chunk
  tests also cover this — they must keep passing);
- code_paths entry naming a missing file blocks; a directory entry passes.

### Step 4: `ve subsystem validate` verifies code_references

In src/subsystems.py, add
`validate_code_references(self, subsystem_id) -> tuple[list[str], list[str]]`:
iterate the parsed frontmatter's `code_references`, run each through
`check_reference_target` against `self.project_dir`, collect errors/warnings.

In src/cli/subsystem.py `validate`: call it alongside `validate_chunk_refs`;
print all errors (exit 1 if any), echo warnings on success.

Tests first in tests/test_subsystem_validate.py:
- subsystem whose ref names a real file+symbol passes;
- invented symbol in an existing file → exit 1, output names the symbol and
  the ref;
- missing file → exit 1;
- file-only ref to an existing non-Python file passes;
- chunk-ref validation behavior unchanged.

### Step 5: Skill template updates (write-time verification in the flows)

Edit `src/templates/plugin/skills/subsystem-discover.md.jinja2`:
- allowed-tools: add `"Bash(ve subsystem validate:*)"`.
- Phase 4 (Implementation Mapping): add a rule before formatting refs —
  never write a symbol name you have not read from the target file in this
  session; open the file and copy the definition's name exactly (a
  plausible-but-invented name is precisely the defect this rule kills).
- Phase 4 documentation steps: after updating frontmatter, run
  `ve subsystem validate <subsystem_id>`; every reported missing
  file/symbol is a generator error to fix now. Update Exit Criteria to
  include the validate pass.
- Phase 7 completeness checklist: add "ve subsystem validate passes".

Edit `src/templates/plugin/skills/chunk-complete.md.jinja2`:
- Step 2: add the copy-don't-reconstruct instruction for symbol names.
- Step 4: note that `ve chunk validate` now **fails** on references naming
  nonexistent files/symbols and `ve chunk complete` refuses to land them;
  the remedy is fixing the reference or the code — never deleting a
  reference to pass the gate (deliberate-deletion cases go to the operator).

Re-render: `uv run ve plugin render`; commit the updated
`skills/subsystem-discover/SKILL.md` and `skills/chunk-complete/SKILL.md`.
Verify tests/test_plugin_render.py passes.

### Step 6: Full-suite verification and self-application

- `uv run pytest tests/ -q` — full suite green against the recorded baseline.
- `uv run ve validate` — clean.
- `uv run ve chunk validate crossref_generator_verify` once code_references
  are populated at completion — the chunk lands through its own gate.

## Dependencies

None on unshipped work. `depends_on: []` stands: the shared check builds on
ACTIVE machinery (`symbols.extract_symbols`, `crossref_rename_integrity`'s
loud-failure precedent). Siblings in this narrative touch adjacent code
(src/integrity.py, src/workspace_validation.py) but not the functions changed
here.

## Risks and Open Questions

- **Existing tests completing chunks with populated-but-stale refs**: the new
  complete gate may surface fixture chunks whose code_references point at
  nothing. Expected and desirable; fix fixtures to reference real files (or
  leave refs empty where the test's subject is unrelated).
- **Warning-to-error promotion blast radius**: orchestrator flows that run
  `ve chunk validate` will now fail on stale refs. That is the intended
  behavior change; verify no orchestrator test encodes the old tolerance.
- **Interaction with crossref_glob_refs** (same narrative, may run
  concurrently): that chunk adds glob expansion to
  `IntegrityValidator._validate_chunk_file_paths` and workspace validation.
  If it lands first, the completion gate here should route code_paths checks
  through the same expansion; if this chunk lands first, note the handoff so
  the glob chunk extends `validate_chunk_references_exist` too.
- **Non-Python silent pass**: `check_reference_target` deliberately keeps
  the silent pass for non-Python symbol anchors — surfacing UNCHECKED
  belongs to crossref_unchecked_anchors; do not fork that semantics here.

## Deviations

- **Whole-word fallback before declaring symbol absence** (Step 1, discovered
  during completion): AST extraction only indexes functions and classes, so a
  reference to a module-level constant (live case:
  `docs/chunks/intent_principles` referencing
  `src/models/chunk.py#VALID_CHUNK_TRANSITIONS`) would have become a *false
  error* under the warning→error promotion. `check_reference_target` now
  falls back to a whole-word scan of the symbol's leaf component: name occurs
  in the file without being a def/class → uncheckable warning ("occurs but
  cannot be verified"); name absent entirely → error. Invented names
  (`OriginationSimulator`) still fail because they occur nowhere. Covered by
  three added disposition tests.
- **Stale-ref repairs in overlapping chunks** (completion phase): deleting
  the redundant `_validate_symbol_exists` invalidated code_references in
  three ACTIVE chunks (`chunk_validate`, `chunk_validator_extract`,
  `symbolic_code_refs`); each was re-pointed at the surviving
  `_validate_symbol_exists_with_context`, verified via the new gate itself.
