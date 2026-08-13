

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The 31-character cap has a single origin: `validate_identifier` in
`src/validation.py` defaults `max_length=31`, and two call sites repeat that
arbitrary number explicitly:

1. `src/models/shared.py#_require_valid_dir_name` (`max_length=31`) — the only
   validator behind `ExternalArtifactRef.artifact_id`. This is what makes
   36-character artifact names like `database_and_sagemaker_savings_plans`
   unrepresentable in external.yaml pointers (the 3 field defects).
2. `src/cli/utils.py#validate_short_name` (`max_length=31`) — governs artifact
   creation (`ve chunk create`, `ve narrative create`, `ve investigation
   create`, `ve subsystem discover`).

The audit for other same-origin caps found none: the remaining `max_length`
uses are real external constraints (GitHub's 39-char org / 100-char repo limits
in `_require_valid_repo_ref`) or explicit opt-outs (`max_length=None` for
ticket ids and member qualifiers). `validate_member_name` in
`models/workspace.py` has no length cap at all.

The real constraint on an artifact id is path legality: an artifact id becomes
a directory name, and every filesystem we care about (APFS, ext4, NTFS) caps a
path component at 255 bytes. The identifier charset is pure ASCII
(`[a-zA-Z0-9_.-]`), so characters == bytes and a 255-character cap is exactly
the filesystem limit. The charset check (which is also a real constraint —
it is what keeps ids shell-safe and unambiguous against `::`/`/` qualifiers)
stays unchanged.

Plan: introduce `MAX_PATH_COMPONENT_LENGTH = 255` in `src/validation.py`, make
it the default `max_length`, and drop the explicit `31` at both call sites so
they inherit the real constraint. Both validators then agree by construction —
a pointer can never name an artifact that local creation refuses.

TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first for the
field-defect case (36-char artifact_id in ExternalArtifactRef, 36-char
`ve chunk create`) and the new 255/256 boundary, then flip the implementation.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (backreferenced by both
  `src/validation.py` and `src/models/shared.py`): this chunk USES the
  subsystem's validation helpers and tightens their documented rationale; it
  does not change the artifact lifecycle pattern itself.

## Sequence

### Step 1: Failing tests for the lifted cap

- `tests/test_task_models.py` (`TestExternalArtifactRef`): accept
  `artifact_id="database_and_sagemaker_savings_plans"` (36 chars, the field
  defect); accept a 255-char id; reject a 256-char id with a message naming
  255; still reject charset violations (spaces).
- `tests/test_validation.py`: default cap is `MAX_PATH_COMPONENT_LENGTH`
  (255) — 36-char and 255-char values pass with no explicit `max_length`,
  256-char values fail; explicit `max_length` still honored (existing tests).
- `tests/test_chunk_start.py`: a 36-char descriptive name is accepted by
  `ve chunk create`; 255-char accepted; 256-char rejected.
- `tests/test_narrative_create.py`: same for `ve narrative create`.

Run the suite; the new tests must fail against the current 31-char cap.

### Step 2: Lift the cap at its origin

In `src/validation.py`: add `MAX_PATH_COMPONENT_LENGTH = 255` with a comment
explaining it is the filesystem path-component limit (bytes == chars for the
ASCII identifier charset), change `validate_identifier`'s default to it, and
add a chunk backreference.

### Step 3: Remove the arbitrary caps at call sites

- `src/models/shared.py#_require_valid_dir_name`: drop `max_length=31`
  (inherits the 255 default). Leave the GitHub 39/100 caps in
  `_require_valid_repo_ref` untouched — they are real external constraints.
- `src/cli/utils.py#validate_short_name`: drop `max_length=31`.

Add chunk backreferences at both sites.

### Step 4: Update stale tests asserting the old cap

- `tests/test_chunk_start.py`: `test_rejects_length_32_or_more` and the
  `TestCombinedNameLengthValidation` class assert 32-40 char names are
  rejected; rewrite them around the 255/256 boundary and update docstrings.
  `test_collects_all_errors` uses a 33-char name expecting both a length and
  a charset error; keep it multi-error by exceeding 255.
- `tests/test_narrative_create.py`: same treatment for its copies.

### Step 5: Update SPEC.md

Replace `^[a-zA-Z0-9_-]{1,31}$` with `^[a-zA-Z0-9_-]{1,255}$`, "exceeds 31
characters" with "exceeds 255 characters", and update the Limits table
(SHORT_NAME length / Chunk name length: 255 characters, noting the filesystem
path-component origin).

### Step 6: Full verification

`uv run pytest tests/` green; `uv run ve validate` clean.

---

**BACKREFERENCE COMMENTS**

Add `# Chunk: docs/chunks/crossref_artifact_id_cap` at the modified symbols
(`MAX_PATH_COMPONENT_LENGTH`/`validate_identifier`, `_require_valid_dir_name`,
`validate_short_name`).

## Risks and Open Questions

- Byte-vs-character equivalence holds only because the identifier charset is
  ASCII; the comment on the constant records this so a future charset widening
  revisits the cap.
- Test directories up to 255 chars are created under pytest tmp paths; total
  path stays far below macOS/Linux `PATH_MAX`, and the component itself is at
  the limit, not over it, so creation succeeds on APFS/ext4/NTFS.
- SPEC.md's limits table is prose, not code — grep for every `31` tied to
  name length to avoid leaving a stale statement.

## Deviations

None. The implementation followed the planned sequence; the same-origin audit
confirmed no additional arbitrary caps beyond the two identified at planning
time.
