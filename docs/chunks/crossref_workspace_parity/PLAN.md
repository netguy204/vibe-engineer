

# Implementation Plan

## Approach

Two validators check chunk-declared file references today, and they disagree:

- Single-tree: `src/integrity.py#IntegrityValidator::_validate_chunk_file_paths`
  checks **both** `code_paths` and `code_references` file parts with
  `Path.exists()` (directories accepted), gated on chunk status
  ACTIVE/COMPOSITE (FUTURE/IMPLEMENTING legitimately list files they expect to
  create; HISTORICAL/SUPERSEDED keep archaeological references).
- Workspace: `src/workspace_validation.py#_Validator::check_code_references`
  checks **only** `code_references`, with `Path.is_file()` (directories
  rejected — the 7 unfixable Cloud Capital defects), and with **no status
  gating** (so a HISTORICAL chunk's archaeological refs would defect in
  workspace mode but pass single-tree).

The fix brings the workspace side to the single-tree semantics, changing only
`check_code_references`:

1. **Directory acceptance**: replace `target.is_file()` with
   `target.exists()`. When the target exists but is not a file (a directory),
   skip the symbol-anchor check — a symbol cannot be looked up in a
   directory, and the single-tree check never inspects symbols at all.
2. **`code_paths` validation**: chunks (`ChunkFrontmatter`) carry
   `code_paths`; subsystems (`SubsystemFrontmatter`) do not. Check each
   `code_paths` entry through the same path-resolution logic as a
   `code_references` file part (same `::`-qualified → unverified routing,
   same `.exists()` test, same `UNRESOLVABLE_FRONTMATTER` fix class), so
   the two fields cannot drift semantically inside the workspace validator
   either.
3. **Status gating for chunks**: when the artifact is a chunk, skip the
   check unless status is ACTIVE or COMPOSITE — mirroring
   `_validate_chunk_file_paths` and its rationale verbatim. Subsystem
   references stay checked for every subsystem status: single-tree has no
   competing subsystem file check, so there is no disagreement to
   reconcile, and subsystem `code_references` document living patterns
   regardless of documentation status.

No change is needed on the single-tree side: it already accepts directories
and already checks `code_paths`. Symbol checking remains a workspace-only
extra (later narrative chunks — `crossref_reexport_absence`,
`crossref_unchecked_anchors` — refine it); "parity" here is about which
declared paths are checked and what counts as existing.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md: behavior-level tests
through `validate_workspace`, using the existing tmp-path workspace fixtures
in tests/test_workspace_validation.py. One single-tree test is added to
tests/test_integrity.py pinning the directory-acceptance semantics the
workspace side is being aligned to, so the parity contract is stated on both
sides.

## Sequence

### Step 1: Restructure `check_code_references` around a shared path check

In `src/workspace_validation.py`:

- Parse frontmatter as today; return early only when frontmatter is None or
  when *both* `code_references` and `code_paths` (via
  `getattr(frontmatter, "code_paths", [])`) are empty.
- For chunk artifacts, return early unless
  `frontmatter.status in (ChunkStatus.ACTIVE, ChunkStatus.COMPOSITE)`,
  with a comment citing the single-tree rationale (import `ChunkStatus`
  from `models`).
- Extract a small local helper (closure or method) that, given a reference
  string, a field name, and the file part, performs: qualified (`::`) →
  append `UnverifiedReference`; `not (member_root / file_part).exists()` →
  `UNRESOLVABLE_FRONTMATTER` defect. The defect message names the field
  (`code_paths` / `code_references`) so fix loops know which frontmatter
  entry to edit.
- `code_paths` entries run through the helper with the whole entry as the
  file part (no `#` splitting — the field is plain paths).
- `code_references` entries run through the helper, then keep the existing
  symbol-absence check, additionally guarded by `target.is_file()` so a
  directory target skips symbol lookup explicitly rather than via the
  `IsADirectoryError`-is-an-`OSError` accident.
- Add chunk backreference comments for this chunk at the method level.

### Step 2: Workspace tests

In `tests/test_workspace_validation.py` (extend the existing
"Frontmatter code_references" section; add a `code_paths` helper mirroring
`code_ref_chunk`):

- code_references entry naming an existing **directory** → clean (the Cloud
  Capital `packages/libs/env-config` case).
- code_references entry naming a missing path still defects (regression
  guard on the `.exists()` swap).
- directory target with a `#symbol` anchor → clean, symbol check skipped.
- chunk `code_paths` entry naming a missing file → `UNRESOLVABLE_FRONTMATTER`
  defect whose message says `code_paths` (the rot-invisibly gap).
- chunk `code_paths` entry naming an existing directory → clean.
- chunk with `code_paths` but empty `code_references` is still scanned
  (guards the early-return restructure).
- HISTORICAL chunk with a stale `code_references`/`code_paths` entry → clean
  (status-gating parity); FUTURE chunk likewise.
- subsystem stale `code_references` still defects regardless of subsystem
  status (subsystem scope unchanged).

### Step 3: Single-tree parity pin

In `tests/test_integrity.py`, add a test asserting an ACTIVE chunk whose
`code_paths`/`code_references` entry names an existing **directory** passes
`_validate_chunk_file_paths` — the semantics workspace mode now agrees with.

### Step 4: Full validation

- `uv run pytest tests/` — full suite.
- `uv run ve validate` — clean.
- Update this chunk's GOAL.md `code_paths` (planning-time) and, after
  implementation, `code_references`.

## Dependencies

None. `crossref_defect_line_anchor`, `crossref_glob_refs`, and
`federation_member_refs` depend on this chunk landing first (narrative
prompts 1, 3, 4), which is a reason to keep the restructure in Step 1 small
and legible — those chunks will edit the same method.

## Risks and Open Questions

- **Status gating is a behavior change beyond the two named fixes**: a
  workspace containing HISTORICAL/FUTURE chunks with stale refs stops
  defecting on them. This is exactly what "the two validators must agree on
  semantics" requires — single-tree deliberately exempts those statuses —
  but it will change defect counts on existing workspaces (downward, on
  legitimate grounds).
- Directory-with-symbol-anchor (`pkg/dir#Symbol`) is accepted silently.
  A later narrative chunk (`crossref_unchecked_anchors`) introduces the
  UNCHECKED disposition that would make this visible; inventing a partial
  version here would fork that design.
- `parse_frontmatter` failures (returns None) keep today's silent-skip
  behavior; changing that is out of scope.

## Deviations

- Step 3: tests/test_integrity.py already pinned directory acceptance for
  `code_paths` (`test_directory_code_path_exists_clean`, from
  crossref_rename_integrity), so only the `code_references`-file-part
  directory pin was added (`test_directory_code_reference_exists_clean`).
- Step 1: the shared helper became a closure (`resolve_path`) returning the
  existing target path (or None after recording the disposition), which let
  the symbol check reuse its result instead of re-resolving.
