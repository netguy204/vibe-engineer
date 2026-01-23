# Implementation Plan

## Approach

This implementation adds magic markers to CLAUDE.md that delineate VE-owned content from
user customizations. The approach follows the existing template rendering pattern in the
codebase, specifically extending `src/project.py` to detect markers and perform
marker-aware rewriting.

**Key patterns used:**
- Template rendering via `render_template()` from `src/template_system.py`
- Idempotent initialization pattern established in `Project.init()`
- Test-driven development per `docs/trunk/TESTING_PHILOSOPHY.md`

**Marker syntax:**
```
<!-- VE:MANAGED:START -->
... VE-generated content ...
<!-- VE:MANAGED:END -->
```

HTML comments ensure markers are invisible when rendered. The `VE:` prefix avoids
conflicts with other tools.

## Sequence

### Step 1: Write failing tests for marker detection and preservation

Create tests in `tests/test_project.py` that verify:
- New CLAUDE.md files include magic markers
- Existing CLAUDE.md with markers: content inside markers is rewritten
- Existing CLAUDE.md with markers: content outside markers is preserved
- Existing CLAUDE.md without markers: file is unchanged (unchanged behavior)
- Edge cases: malformed markers result in warnings, file left unchanged

These tests will fail initially because the functionality doesn't exist.

Location: `tests/test_project.py` (extend `TestProjectInit` class)

### Step 2: Update CLAUDE.md template with magic markers

Add `<!-- VE:MANAGED:START -->` and `<!-- VE:MANAGED:END -->` markers to the template,
wrapping the VE-managed content. This determines what gets rewritten on subsequent
`ve init` runs.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 3: Implement marker parsing logic

Create a helper module (or function in `project.py`) that:
- Detects presence of magic markers in a file
- Extracts content before, inside, and after markers
- Validates marker integrity (START before END, both present or neither)
- Returns structured result for rewriting logic

Location: `src/project.py` (new private methods) or `src/magic_markers.py`

### Step 4: Update `_init_claude_md()` to use marker-aware rewriting

Modify the existing `_init_claude_md()` method in `src/project.py` to:
1. If CLAUDE.md doesn't exist → create with markers (current behavior, but with markers)
2. If CLAUDE.md exists without markers → skip (current behavior, backward compatible)
3. If CLAUDE.md exists with markers → rewrite content inside markers, preserve outside

This is the core behavioral change that enables legacy projects to receive updated
VE prompting.

Location: `src/project.py`

### Step 5: Handle edge cases and add warnings

Add appropriate handling for:
- Malformed markers (missing START or END): warn and skip
- Markers in wrong order (END before START): warn and skip
- Multiple marker pairs: not supported, warn and skip

Warnings should appear in `InitResult.warnings` so operators see them.

Location: `src/project.py`

### Step 6: Verify all tests pass

Run the test suite to ensure:
- New tests pass
- Existing tests still pass (no regression)
- Idempotency behavior is preserved for files without markers

Location: Command line (`uv run pytest tests/test_project.py tests/test_init.py`)

### Step 7: Update GOAL.md code_paths

Add references to the files modified during implementation.

Location: `docs/chunks/claudemd_magic_markers/GOAL.md`

## Dependencies

- The `external_resolve_enhance` chunk is listed in `created_after` in the frontmatter
  but doesn't block this work functionally; this chunk can proceed independently.

## Risks and Open Questions

- **Multiple marker pairs**: The goal document mentions this as an edge case. The
  simplest approach is to not support multiple pairs and warn. If a use case emerges,
  we can extend later.

- **Template rendering context**: Need to ensure the marker-wrapped content renders
  correctly with the same context variables (`ve_config`) used in full file rendering.

- **Test isolation**: Tests must verify that existing CLAUDE.md files without markers
  are truly unchanged (byte-for-byte identical) to ensure backward compatibility.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
