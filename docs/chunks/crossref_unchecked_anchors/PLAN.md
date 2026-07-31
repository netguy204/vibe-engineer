

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The symbol checkers have three silent blind spots, and this chunk makes each
one say so — without adding any new resolution logic:

1. **Workspace mode** (`ve workspace validate`, `src/workspace_validation.py`):
   `_symbol_is_absent` returns `None` ("may exist") when the anchor's last
   `::` component fails `str.isidentifier()` — the same undecidable signal
   that makes `name_is_reexport_only` return `None`. A dotted/bracketed
   anchor (`jobs.Checks.steps[Seed workspace .venv]`) therefore silently
   passes. The fix: `_symbol_is_absent` grows a disposition tag — it returns
   `("absent", name, reason)` or `("unchecked", name, reason)` or `None`
   ("checked; may exist") — and `check_code_references` routes the
   `"unchecked"` disposition into the existing `UnverifiedReference`
   mechanism (the same one `crossref_glob_refs` uses for symbol anchors on
   glob patterns; no second mechanism is added). Two adjacent silent skips in
   the same loop — a symbol anchor on a directory target and a symbol anchor
   on an unreadable file — become `UnverifiedReference` entries too, because
   they are the same lie ("clean run" implying coverage that never happened).

2. **Single-tree mode** (`check_reference_target` in `src/symbols.py`, shared
   by `ve chunk validate`, the completion gate, and `ve subsystem validate`):
   a symbol anchor on a non-Python file returns `(None, None)` — the
   docstring explicitly defers honest UNCHECKED reporting to this chunk —
   and a non-identifier leaf on a Python file falls into a whole-word regex
   whose `\b` semantics around brackets/dots are undefined behavior for this
   purpose. Both become warnings (the existing "uncheckable" channel: never
   errors, so nothing new gates), keyed off the same `isidentifier()` signal.

3. **Coverage counts**: operators can only see what the validator is not
   seeing if the counts are printed.
   - `ValidationReport` gains `symbol_anchors_checked` /
     `symbol_anchors_unchecked` counters, surfaced in the JSON `counts` block
     and the text renderer. "Unchecked" folds in every uncheckable-symbol
     disposition: non-identifier anchors, glob-pattern anchors, anchors on
     cross-repo-qualified refs, directory targets, unreadable targets.
     Anchors whose *file part* is already a defect are not counted — the ref
     is already gating, and the count describes the checker's blind spots,
     not its queue.
   - `ve validate` (single-tree `IntegrityValidator`) checks declared file
     parts only and runs no symbol checker at all, so every symbol anchor on
     a status-gated (ACTIVE/COMPOSITE) chunk is unchecked there. It gains a
     `symbol_anchors_unchecked` count and one always-printed output line
     (same precedent as the allowlist suppression count) pointing at the
     commands that do check symbols. Counting only a "never-checkable"
     subset would imply the rest were checked — which would be dishonest.

No new resolution capability is added anywhere: every change reclassifies an
existing silent pass into a stated disposition, or counts dispositions that
already exist.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): `src/symbols.py` and
  the validators sit inside this subsystem's scope. This chunk follows the
  established error/warning contract (`check_reference_target` returning
  `(error, warning)`) rather than changing it. No new deviations discovered.

## Sequence

### Step 1: UNCHECKED disposition in `check_reference_target` (src/symbols.py)

- Non-Python file part with a symbol anchor: return a warning
  (`Symbol anchor '{symbol_path}' in non-Python file {file_path} is not
  checked (ref: {ref})`) instead of `(None, None)`.
- Python file whose anchor leaf fails `str.isidentifier()` (including the
  empty leaf of a trailing `#`): return a warning before the whole-word
  regex runs (`Symbol anchor '{symbol_path}' is not a checkable identifier
  and is not checked in {file_path} (ref: {ref})`). Placed after the
  file-existence check, before symbol extraction — a non-identifier can
  never appear in `extract_symbols` output.
- Update the docstring: the `(None, None)` "not symbol-checkable" case is
  gone; verified is the only silent outcome.

Tests (tests/test_symbols.py):
- Update `test_non_python_symbol_anchor_is_skipped` → now expects a warning.
- New: bracketed YAML-style anchor on a Python file → warning, not error.
- New: trailing-`#` empty anchor → warning, not error.

### Step 2: Disposition tag on `_symbol_is_absent` (src/workspace_validation.py)

Change the return contract from `(name, reason) | None` to
`(disposition, name, reason) | None` with `disposition ∈ {"absent",
"unchecked"}`. The `not name or not name.isidentifier()` branch — which
today returns `None` — returns `("unchecked", name, "is not a checkable
identifier; only plain identifier names are symbol-checked")`. The two
absence branches keep their reasons and gain the `"absent"` tag.

### Step 3: Route dispositions and count coverage in `check_code_references`

In the symbol-anchor loop of `check_code_references`:
- Add `symbol_anchors_checked` / `symbol_anchors_unchecked` counters to
  `_Validator.__init__`.
- Cross-repo-qualified ref with a symbol anchor: already unverified (whole
  ref); count unchecked.
- Glob-pattern anchor: existing unverified entry; count unchecked.
- Directory target: currently `continue` — emit `UnverifiedReference`
  ("symbol anchor on a directory; a symbol cannot be looked up in a
  directory") and count unchecked.
- Unreadable target: currently `continue` — emit `UnverifiedReference`
  ("target file could not be read; symbol anchor is not checked") and count
  unchecked.
- `_symbol_is_absent` returns `"unchecked"`: emit `UnverifiedReference`
  naming the anchor and reason; count unchecked.
- `_symbol_is_absent` returns `"absent"` or `None`: count checked
  (`"absent"` keeps producing the same defect as today).
- File-part defect (missing file, empty glob): counted neither way.

### Step 4: Surface the counts in workspace report and CLI

- `ValidationReport`: add `symbol_anchors_checked` and
  `symbol_anchors_unchecked` fields; include both in `to_dict()["counts"]`;
  thread them through `_Validator.run()`.
- `src/cli/workspace.py` `_render_report`: print a coverage line whenever
  any symbol anchors were seen — e.g.
  `Symbol anchors: N checked, M unchecked (unchecked anchors are listed in
  the JSON report's "unverified" entries).` Also generalize the existing
  unverified summary line, which currently claims all unverified entries are
  cross-repository targets and is no longer accurate.

Tests (tests/test_workspace_validation.py):
- Non-identifier anchor on a YAML file in a member chunk → no defect, one
  unverified entry with an identifier-mentioning reason, unchecked count 1.
- Plain identifier anchor that verifies → checked count 1, unchecked 0.
- Extend the glob-anchor and directory-target tests to assert the unchecked
  count / new unverified entry.
- `to_dict()["counts"]` carries both numbers.

### Step 5: UNCHECKED count in `ve validate` (src/integrity.py, src/cli/init_cmd.py)

- `IntegrityResult`: add `symbol_anchors_unchecked: int = 0`.
- `IntegrityValidator._validate_chunk_file_paths` already iterates every
  status-gated chunk's `code_references`; accumulate a count of refs with a
  non-empty symbol part (instance counter, folded into the result in
  `validate()`).
- `src/cli/init_cmd.py` `validate`: when the count is nonzero, print (outside
  the verbose block, same rationale as the suppression line):
  `N symbol anchor(s) not checked: ve validate verifies declared file paths
  only. Symbol checking runs in ve chunk validate, ve subsystem validate,
  and ve workspace validate.`

Tests (tests/test_integrity.py): ACTIVE chunk with `file#symbol` refs yields
the count; FUTURE/HISTORICAL chunks do not contribute; CLI line appears.

### Step 6: Completion-gate behavior pin (tests/test_chunk_complete_gate.py)

One test: a chunk whose `code_references` includes a non-Python symbol
anchor completes with a warning, not an error — UNCHECKED reports honestly
but never gates.

### Step 7: Full-repo verification

`uv run pytest tests/ -q` (baseline 4841 passed) and `uv run ve validate` on
this repo — the new `ve validate` line will now itself appear (this repo's
ACTIVE chunks declare many symbol anchors), which is the feature working,
not a failure. Exit code must remain 0.

## Dependencies

- `crossref_reexport_absence` (ACTIVE, merged): `name_is_reexport_only`
  returning `None` for non-identifiers is the undecidable signal this chunk
  keys off.
- `crossref_glob_refs` (ACTIVE, merged): the glob symbol-anchor unverified
  disposition this chunk folds into the coverage counts.
- `crossref_workspace_parity` (ACTIVE, merged): the workspace
  `check_code_references` structure being extended.

## Risks and Open Questions

- `ve validate` on this repository will print a large not-checked count
  every run (every ACTIVE chunk's symbol refs). Accepted: one line, honest,
  and the alternative (counting only a subset) implies coverage that does
  not exist.
- New warnings from `check_reference_target` flow into `ve chunk validate`,
  the completion gate, and `ve subsystem validate` for existing artifacts
  with non-Python symbol anchors. Warnings never gate, so nothing breaks;
  operators see new lines, which is the point.
- `refactor_move.py` mirrors `check_reference_target` semantics for its own
  evidence gathering; it is not a validator and reports its own
  dispositions, so it is deliberately untouched.

## Deviations

(Populated during implementation if reality diverges from the plan.)
