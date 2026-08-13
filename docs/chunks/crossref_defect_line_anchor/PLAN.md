

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug lives entirely in `src/workspace_validation.py`'s
`check_code_references`. Its `resolve_path` closure (and the symbol-absence
defect after it) anchor every finding with `_find_line(content, reference)`,
which returns the **first textual occurrence** of the reference string anywhere
in GOAL.md. Because `code_paths` precedes `code_references` in frontmatter, a
path that appears in both fields anchors on the `code_paths` line — and a fix
loop that trusts `line` edits the wrong entry, watches the anchor move, and
makes no progress.

The fix: introduce a field-aware line finder,
`_find_field_entry_line(content, field_name, needle)`, that

1. locates the top-level frontmatter key line (`code_paths:` or
   `code_references:`),
2. scans only the lines belonging to that field's YAML block (indented lines
   and zero-indent `- ` list items, stopping at the next top-level key or the
   closing `---` fence), and
3. returns the first line **within that block** containing the needle,
   falling back to `_find_line(content, needle)` when the field block cannot
   be found (defensive: unusual YAML styles must degrade to today's behavior,
   never to `None`-when-present).

`resolve_path` already receives `field_name` for its messages, so it passes
that same name to the finder for both the unverified and the defect
dispositions. The symbol-absence defect passes `"code_references"` explicitly.

Both list-item styles must be handled because real frontmatter in this repo
uses zero-indent items (`code_references:\n- ref: ...`) while the test helper
writes two-space-indented items — YAML permits both.

The pointer checks (`repo:`, `tree:`, `artifact_id:`) keep plain `_find_line`;
those needles are field names themselves and are not the reported bug.

The single-tree validator (`integrity.IntegrityValidator
._validate_chunk_file_paths`) reports no line numbers at all, so no parity
change is needed there — /validate-fix is affected only insofar as it consumes
workspace reports.

Tests follow docs/trunk/TESTING_PHILOSOPHY.md: behavioral tests through
`validate_workspace` asserting the reported `line` lands on the offending
entry, including the regression case where the same path appears in both
fields.

## Sequence

### Step 1: Add `_find_field_entry_line` helper

In `src/workspace_validation.py`, next to `_find_line`, add
`_find_field_entry_line(content: str, field_name: str, needle: str) -> int | None`:

- Iterate lines with 1-indexed numbers.
- On finding the line whose stripped form starts the field
  (`line.startswith(f"{field_name}:")` at zero indentation), enter the block.
- While in the block, a line belongs to the field if it starts with whitespace
  or is a list item (`- ` prefix, but not the `---` fence). The first
  in-block line containing `needle` is the answer.
- Leaving the block (next top-level key or `---`) or exhausting the file
  without a hit falls back to `_find_line(content, needle)`.
- Backreference comment: `# Chunk: docs/chunks/crossref_defect_line_anchor`.

### Step 2: Anchor `check_code_references` findings on the owning field

- In `resolve_path`, replace both `_find_line(content, reference)` calls
  (unverified disposition and missing-target defect) with
  `_find_field_entry_line(content, reference, field_name)` — the closure
  already receives `field_name`.
- In the symbol-absence defect at the bottom of `check_code_references`,
  replace `_find_line(content, ref)` with
  `_find_field_entry_line(content, ref, "code_references")`.

### Step 3: Tests

In `tests/test_workspace_validation.py`, in the frontmatter section:

1. **The regression:** a chunk listing the same missing path in `code_paths`
   and in `code_references` (`src/gone.py` and `src/gone.py#Widget`) produces
   two `UNRESOLVABLE_FRONTMATTER` defects, and each `line` points at its own
   field's entry — the `code_references` defect's line is the `- ref:` line,
   not the `code_paths` line.
2. **Symbol-absence anchoring:** an existing file whose symbol is gone, with
   the same file path also present in `code_paths`, anchors the defect on the
   `code_references` entry line.
3. **Unverified anchoring:** a qualified ref present in both fields anchors
   each unverified entry on its own field's line.
4. **Zero-indent YAML list style:** a chunk written with
   `code_references:\n- ref: src/gone.py` (no indentation, the style `ve`
   itself emits) still gets the correct line.
5. Existing tests (`defect.line == 4` in
   `test_code_reference_to_a_missing_file_is_unresolvable_frontmatter`)
   continue to pass unchanged.

### Step 4: Full test run and validation

- `uv run pytest tests/` — no new failures against the inherited baseline.
- `uv run ve validate` — clean.
- Update GOAL.md `code_references` at completion time.

## Risks and Open Questions

- YAML flow-style lists (`code_paths: [a, b]`) would not match the block
  scanner's line shapes; the fallback to `_find_line` preserves today's
  behavior for such exotic frontmatter rather than regressing to no line.
- Duplicate identical entries *within one field* anchor on the first — both
  are the same defect and `run()` deduplicates on
  `(fix_class, path, line, reference)` anyway.
- A needle quoted inside an *earlier* entry's `implements:` string in the same
  field would attract the anchor one entry early. Still inside the right
  field, and the defect's `reference` remains the authoritative key for fix
  loops; a token-boundary match is not worth its complexity here.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
