

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Introduce a single shared glob-expansion helper and route every path-existence
check that validates chunk-declared paths (`code_paths` and the file part of
`code_references`) through it. The helper lives in `src/symbols.py` alongside
`check_reference_target`, which is already the shared existence check for
reference-emitting flows — this keeps "what counts as present" defined in one
place.

Semantics (fixed by the chunk goal):

- A file part containing glob magic (`*`, `?`, `[`) is a **pattern**, not a
  literal path.
- Validators expand the pattern against the project/member root with
  `pathlib.Path.glob` and **error only when the expansion is empty**.
- A non-empty expansion is a verified reference. No per-match existence
  bookkeeping — the pattern itself is the declared intent ("this applies
  uniformly across everything matching this shape").
- Symbol anchors on glob refs (`pkg/*/mod.py#Symbol`) are **not** checked
  across the expansion. They are reported as uncheckable (a warning in
  `check_reference_target`, an `UnverifiedReference` in workspace validation)
  rather than silently passed — honest reporting, consistent with the
  narrative's crossref_unchecked_anchors direction, without new resolution
  logic.

Four sites change, identified by the wave-1 handoffs:

1. `src/integrity.py#IntegrityValidator::_validate_chunk_file_paths` — the
   `check()` closure (single-tree `ve validate`).
2. `src/workspace_validation.py#check_code_references` — the `resolve_path`
   closure (workspace mode). The parity contract documented on this function
   ("the two validators cannot teach contradictory lessons") extends to glob
   semantics.
3. `src/chunk_validation.py#validate_chunk_references_exist` — the completion
   gate's `code_paths` loop (its `code_references` loop already delegates to
   `check_reference_target`).
4. `src/symbols.py#check_reference_target` — the shared existence check used
   by the completion gate, chunk validation, and subsystem validation.

Pattern expansion uses `Path.glob`, wrapped so malformed patterns (absolute
paths, bad syntax) degrade to "no matches" — which surfaces as the empty-glob
error, pointing the operator at the bad pattern rather than crashing.

Tests follow docs/trunk/TESTING_PHILOSOPHY.md: behavior-level tests against
the public validator entry points (`IntegrityValidator.validate`,
`WorkspaceValidator`, `validate_chunk_references_exist`,
`check_reference_target`), exercising both the matching-glob (passes) and
empty-glob (errors) cases, plus the symbol-anchor-on-glob disposition.

Documentation: `docs/trunk/SPEC.md` "Code Reference Format" gains the glob
form so the frontmatter contract is written down where the reference syntax
is specified.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk IMPLEMENTS
  part of the validation surface of the workflow-artifact lifecycle
  (`src/symbols.py` carries this subsystem's backreference). No deviations
  discovered; the change follows the existing shared-check pattern
  (`check_reference_target` as the single arbiter of existence).

## Sequence

### Step 1: Shared glob helpers in src/symbols.py

Add two module-level functions next to `check_reference_target`:

- `is_glob_pattern(file_part: str) -> bool` — true when the string contains
  glob magic (`*`, `?`, `[`).
- `expand_glob(root: Path, pattern: str) -> list[Path]` — `sorted(root.glob(pattern))`,
  with `ValueError`/`NotImplementedError`/`IndexError` degraded to `[]`
  (absolute or malformed patterns count as matching nothing).

Backreference: `# Chunk: docs/chunks/crossref_glob_refs`.

### Step 2: Glob support in check_reference_target

In `src/symbols.py#check_reference_target`, after parsing the reference:
if `is_glob_pattern(file_path)`:

- empty expansion → error: the pattern matches nothing.
- non-empty expansion with a symbol anchor → warning: symbol anchors on glob
  patterns are not checked across expansions.
- non-empty expansion, no symbol → `(None, None)` (verified).

Update the docstring's contract description. This automatically extends glob
support to the completion gate's `code_references` loop and to subsystem
`code_references` validation.

### Step 3: Glob support in the integrity validator

In `src/integrity.py#IntegrityValidator::_validate_chunk_file_paths`, the
`check()` closure branches on `is_glob_pattern(path)`: expand against
`self.project_dir`; empty expansion appends an `IntegrityError` whose message
says the glob matched nothing (distinct from the moved/renamed message for
concrete paths); non-empty expansion passes. Docstring notes the glob
semantics.

### Step 4: Glob support in the workspace validator

In `src/workspace_validation.py#check_code_references`:

- Change the `resolve_path` closure to return `list[Path]` (empty list =
  disposition already recorded). Glob file parts expand against
  `member_root`; empty expansion reports the same
  `UNRESOLVABLE_FRONTMATTER` defect class with a glob-specific message.
  Concrete paths keep current behavior, returning a one-element list.
- In the `code_references` loop, when the file part is a glob and a symbol
  anchor is present, append an `UnverifiedReference` (reason: symbol anchors
  on glob patterns are not checked across expansions) instead of running the
  symbol scan. Non-glob refs keep the existing symbol check on the single
  resolved target.
- Extend the parity docstring to name glob expansion as part of the shared
  contract.

### Step 5: Glob support in the completion gate's code_paths loop

In `src/chunk_validation.py#validate_chunk_references_exist`, the
`code_paths` loop mirrors Step 3: glob entries expand against
`chunks.project_dir`, erroring only on empty expansion. (The
`code_references` loop is already covered via Step 2.)

### Step 6: Tests

- `tests/test_symbols.py`: `check_reference_target` with a matching glob
  (no error), an empty glob (error), and a glob + symbol anchor (warning).
- `tests/test_integrity.py`: ACTIVE chunk with a matching glob in
  `code_paths` and in a `code_references` file part → no errors; empty glob
  → error naming the pattern.
- `tests/test_workspace_validation.py`: matching glob passes, empty glob is
  a defect, glob + symbol anchor lands in unverified.
- `tests/test_chunk_complete_gate.py`: completion gate accepts a matching
  glob in `code_paths`/`code_references`, rejects an empty one.

### Step 7: Documentation

Add the glob-pattern form to `docs/trunk/SPEC.md` "Code Reference Format"
(pattern syntax, empty-expansion-is-error rule, symbol anchors uncheckable on
patterns). SPEC.md is not template-rendered, so a direct edit is correct.

### Step 8: Full test suite + validate

`uv run pytest tests/` and `uv run ve validate` both clean.

## Dependencies

- `crossref_workspace_parity` (ACTIVE, merged): established the shared
  `resolve_path` closure and the two-validator parity contract this chunk
  extends.
- `crossref_generator_verify` (ACTIVE, merged): established
  `check_reference_target` and the completion gate this chunk routes globs
  through.

## Risks and Open Questions

- `Path.glob` behavior varies slightly across Python versions for malformed
  patterns; the try/except degradation to "no matches" makes every variant
  surface as the empty-glob error, which names the pattern.
- Symbol anchors on glob refs could plausibly mean "present in every match";
  we deliberately do not resolve them (reported as uncheckable instead),
  because the goal fixes error conditions to empty expansion only, and
  cross-expansion symbol semantics belong to a future chunk if field evidence
  demands them.

## Deviations

<!-- Populated during implementation. -->
