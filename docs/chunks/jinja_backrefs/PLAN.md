# Implementation Plan

## Approach

Add Jinja backreference comments (`{# Chunk: ... #}`) to source templates to provide traceability from template content back to the chunks that added it. This mirrors the code backreference pattern documented in `docs/trunk/SPEC.md` but uses Jinja comment syntax.

The key insight from the `template_drift` investigation: agents editing templates benefit from understanding why sections exist. Code backreferences (`# Chunk: docs/chunks/foo`) help with Python/JS code; Jinja backreferences (`{# Chunk: docs/chunks/foo #}`) serve the same purpose for templates.

**Format**: `{# Chunk: docs/chunks/<directory> - <brief description> #}`

Jinja comments are stripped during rendering, so these appear only in source templates—exactly what we want for traceability without cluttering rendered output.

**No tests needed**: Per `docs/trunk/TESTING_PHILOSOPHY.md`, "We verify templates render without error and files are created, but don't assert on template prose." The backreference comments are prose/documentation within templates, not behavioral code. Existing template rendering tests already verify templates render correctly (which implicitly verifies the Jinja comment syntax is valid).

## Sequence

### Step 1: Add backreferences to CLAUDE.md.jinja2

Add Jinja backreference comments to sections that were added or modified by prior chunks:

1. **Auto-generated header block (lines 1-9)**: Added by `template_drift_prevention` chunk
   - Add: `{# Chunk: docs/chunks/template_drift_prevention - Auto-generated header for ve source repo #}`

2. **Proposed Chunks section (lines 98-109)**: Restored by `restore_template_content` chunk (originally from commit `62b6d8f`)
   - Add: `{# Chunk: docs/chunks/restore_template_content - Proposed chunks documentation #}`

3. **Development section with uv run instructions (lines 147-165)**: Restored by `restore_template_content` chunk
   - Add: `{# Chunk: docs/chunks/restore_template_content - Development section with uv run instructions #}`

4. **Template Editing Workflow section (lines 166-190)**: Added by `template_drift_prevention` chunk
   - Add: `{# Chunk: docs/chunks/template_drift_prevention - Template editing workflow documentation #}`

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 2: Add backreferences to chunk-plan.md.jinja2

Add Jinja backreference comment to the cluster prefix suggestion step:

1. **Step 2 - Cluster prefix suggestion (lines 22-28)**: Restored by `restore_template_content` chunk (originally from commit `8a29e62`)
   - Add: `{# Chunk: docs/chunks/restore_template_content - Cluster prefix suggestion step #}`

Location: `src/templates/commands/chunk-plan.md.jinja2`

### Step 3: Verify templates render correctly

Run `uv run ve init` to re-render templates and verify:

1. Templates render without Jinja syntax errors
2. Rendered files do NOT contain the `{# ... #}` comments (they should be stripped)
3. Content is otherwise unchanged

### Step 4: Run tests

Run `uv run pytest tests/` to ensure no regressions.

## Dependencies

- **restore_template_content** (ACTIVE): Must be complete so the content we're annotating exists
- **template_drift_prevention** (ACTIVE): Must be complete so the auto-generated header mechanism exists

Both dependencies are satisfied (status: ACTIVE in their GOAL.md frontmatter).

## Risks and Open Questions

None significant. The auto-generated header partial already has a backreference (`{# Chunk: docs/chunks/template_drift_prevention - Auto-generated header partial #}`), confirming this pattern works and is already in use.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.
-->