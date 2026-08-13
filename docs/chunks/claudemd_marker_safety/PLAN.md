

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Three coordinated changes, all centered on the marker contract between the
`claude` templates (`src/templates/claude/AGENTS.md.jinja2`,
`CLAUDE.md.jinja2`) and `parse_markers` / `Project._init_agents_md` in
`src/project.py`:

1. **Self-documenting markers.** The template's START/END lines become
   annotated HTML comments that state the contract on the marker itself:
   everything between them is regenerated and destroyed by `ve init`;
   project content belongs above START or below END. `parse_markers` grows
   regex-based recognition (`<!--\s*VE:MANAGED:START\b.*?-->`, non-greedy,
   DOTALL) so both the historical bare form (`<!-- VE:MANAGED:START -->`)
   and the annotated form parse. The bare constants `MARKER_START` /
   `MARKER_END` remain exported (tests and the migration skill reference the
   bare form), and all existing error messages are preserved. Because
   in-place regeneration splices `rendered_parse.inside` (which includes the
   marker lines), existing files with bare markers are upgraded to annotated
   markers on their next `ve init` — additive, no migration needed.

2. **Seeded safe region on first write.** The template gains content
   *outside* the markers: a short comment block above START (adapted in
   spirit from the field-tested warning wording archived in the scratchpad
   file named by GOAL.md — "this region is yours; the block below is
   regenerated; two regions survive") and a one-line "project-specific
   content goes here" comment below END. Because `_init_agents_md` splices
   only the `inside` segment when updating an existing file, the seeded
   regions land on fresh writes (Case A) and on the Case B rename path's
   fresh content only when the file had no prior before/after — existing
   files keep their own before/after untouched (designed preservation
   behavior, unchanged).

3. **Warn instead of silently dropping.** In the valid-markers update
   branch of `_init_agents_md`, compare the existing block against the
   incoming render line-wise: strip lines, drop blanks, drop marker lines
   (so the bare→annotated marker upgrade never warns), and if the existing
   block contains lines the incoming render does not, append a warning to
   `InitResult.warnings` naming AGENTS.md and telling the operator where the
   content went (git history) and where it belongs (above START / below
   END). Wording stays consistent with the `claudemd_symlink_notice` notice
   vocabulary ("the VE-managed block in AGENTS.md").

The wave-1 golden fixtures (`tests/fixtures/agents_md_single_tree.md`,
`claude_md_single_tree.md`) pin the single-tree render byte-for-byte. This
chunk changes the render deliberately, so the fixtures are regenerated
exactly as the fixture-test docstring in `tests/test_template_system.py`
prescribes: render with a default `TemplateContext` and overwrite the files;
the assertion is never loosened.

Out of scope, on purpose: `src/templates/package/AGENTS.md.jinja2` keeps its
bare markers — that file lives entirely inside the managed block by design
(opting into a full tree replaces it wholesale), and its scaffold is a
one-shot write, not a regeneration target. The `task` collection's AGENTS.md
has no markers at all.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md: behavior-level tests
through `parse_markers` and `Project.init()`, no mocking of the filesystem.

## Subsystem Considerations

- **docs/subsystems/template_system** (DOCUMENTED): this chunk USES the
  rendering path (`render_template` with `TemplateContext`) unchanged; only
  template content and the marker parser around it change. No deviations
  discovered.

## Sequence

### Step 1: Annotated marker recognition in parse_markers

In `src/project.py`, add module-level compiled regexes for the annotated
forms (a marker comment whose annotation may follow the token) and rewrite
`parse_markers` to count/locate via `finditer` instead of exact-string
`count`/`index`. Segment boundaries come from match spans: `before` ends at
the START match start, `inside` runs through the END match end. Keep every
existing error message byte-identical (they say "CLAUDE.md" — historical
wording that tests assert on). Keep `MARKER_START`/`MARKER_END` constants.

Add tests in `tests/test_project.py` (extend the parse-level coverage):
annotated START/END parse; mixed bare/annotated parse; prose that mentions
`VE:MANAGED:START`/`END` mid-comment (the seeded preamble does exactly
this) is not counted as a marker; malformed cases still error.

### Step 2: Self-documenting markers and seeded regions in the templates

Edit `src/templates/claude/AGENTS.md.jinja2` and mirror byte-for-byte in
`src/templates/claude/CLAUDE.md.jinja2`:

- Above START: a short HTML comment (adapted from the archived field
  wording) saying this region is the operator's, the block below is
  regenerated and destroys in-block edits, and both above-START and
  below-END survive.
- START marker annotated in place: regenerated by `ve init`, in-block
  content is destroyed, project content goes above START or below END.
- END marker annotated in place: end of the managed block, content below is
  preserved.
- Below END: one-line "project-specific content goes here" comment.

Add a `{# Chunk: docs/chunks/claudemd_marker_safety ... #}` template comment.

### Step 3: Discarded-content warning in _init_agents_md

Add a private helper `_managed_block_lines(block) -> set[str]` (stripped,
non-blank, non-marker lines) with a chunk backreference. In the
valid-markers branch, compute
`discarded = _managed_block_lines(existing inside) - _managed_block_lines(incoming inside)`;
when non-empty, append a warning to `result.warnings` that names AGENTS.md,
gives the count, says in-block content is destroyed on regeneration, and
directs recovery from git history into the preserved regions. The write
itself is unchanged — preservation of before/after is designed behavior and
is now stated by the markers themselves and by this warning.

### Step 4: Regenerate the golden fixtures

Render `AGENTS.md.jinja2` and `CLAUDE.md.jinja2` with a default
`TemplateContext` and overwrite `tests/fixtures/agents_md_single_tree.md`
and `tests/fixtures/claude_md_single_tree.md` — the deliberate regeneration
the fixture docstring prescribes.

### Step 5: Update marker-shape assumptions in existing tests; add new ones

- `tests/test_template_system.py::test_agents_md_template_has_managed_markers`:
  assert the annotated prefix (`<!-- VE:MANAGED:START`) rather than the bare
  full string.
- `tests/test_project.py::TestMagicMarkers`: tests that `index()` the bare
  marker inside a *freshly generated* file switch to locating segments via
  `parse_markers`; tests that *construct* files with bare markers stay
  bare (that is the compat guarantee under test).

New behavior tests in `tests/test_project.py`:

- Fresh init seeds content outside the markers (non-empty `before` with the
  safe-region comment; non-empty `after`).
- Fresh render's markers are annotated (say "regenerated"/"destroyed").
- Reinit of an untouched fresh file emits no discard warning (idempotent).
- A file whose block is the current render wrapped in *bare* markers
  regenerates without a discard warning (marker upgrade is not a discard)
  and ends up with annotated markers.
- A file with an operator line inside the block gets exactly one warning
  naming AGENTS.md, and the line is gone from the file.
- Existing before/after content is preserved on that same run (designed
  behavior stated, not changed).

### Step 6: Full suite and validation

`uv run pytest tests/` and `uv run ve validate` both clean. Confirm the
legacy-migration tests in `tests/test_init.py` still pass (their first run
now legitimately warns about the legacy in-block content; the
second-run-clean assertion must still hold).

## Risks and Open Questions

- **False positives on template upgrades**: after this chunk, the first
  regeneration following any template content change will warn about
  dropped lines that were old *template* content, not operator content.
  There is no local record of "what the template last produced", so the
  warning wording hedges ("if you added content between the markers...").
  The field reporter ranked silent destruction as the bug; a rare hedged
  false alarm is the accepted cost.
- **Regex over exact string**: non-greedy DOTALL comment matching could in
  principle mis-span if an annotation contained `-->`; the templates we
  ship never do, and bare markers are unaffected.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
