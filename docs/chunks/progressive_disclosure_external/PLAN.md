<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extracts external artifacts documentation from `docs/trunk/ARTIFACTS.md` into a standalone `docs/trunk/EXTERNAL.md` file and updates the CLAUDE.md template to point to the new location.

The approach follows the progressive disclosure pattern established by the `progressive_disclosure_refactor` chunk: situational content lives in dedicated docs/trunk/*.md files, while CLAUDE.md contains only signposts that help agents discover when to read the detailed documentation.

**Key design decisions:**
- External artifacts documentation merits a separate file because multi-repo workflows are a distinct, complex topic that most agents will never need
- The signpost pattern ("Read when" + trigger keywords + link) is already established and working well
- `ve init` already renders docs/trunk files, so no template infrastructure changes are needed

**Testing approach per docs/trunk/TESTING_PHILOSOPHY.md:**
- This is primarily a documentation change, so behavioral tests are limited
- Verify `ve init` renders without errors (existing test coverage)
- Verify existing tests pass (no regressions)
- No new tests required - template content is explicitly out of scope for testing per Testing Philosophy

## Sequence

### Step 1: Create docs/trunk/EXTERNAL.md

Create the new external artifacts reference document with comprehensive multi-repo workflow documentation. Content should cover:

- What external artifacts are (cross-repository pointers)
- The external.yaml file structure
- How to resolve external artifacts (`ve external resolve`)
- Common scenarios (task directories, shared narratives, cross-repo investigations)
- The relationship between external.yaml and local paths

Use the existing content from `docs/trunk/ARTIFACTS.md#external-artifacts` as the starting point, but expand with additional context appropriate for a standalone reference doc.

Location: `docs/trunk/EXTERNAL.md`

### Step 2: Update CLAUDE.md.jinja2 signpost

Update the External Artifacts signpost in CLAUDE.md.jinja2 to point to `docs/trunk/EXTERNAL.md` instead of `docs/trunk/ARTIFACTS.md#external-artifacts`.

The signpost already follows the correct pattern:
```markdown
### External Artifacts

Cross-repository artifact pointers (`external.yaml` files). **Read when**: encountering `external.yaml` files or working in multi-repo contexts.

See: `docs/trunk/EXTERNAL.md`
```

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 3: Update ARTIFACTS.md to remove external section

Remove the `## External Artifacts {#external-artifacts}` section from ARTIFACTS.md since the content now lives in EXTERNAL.md. Add a brief mention and cross-reference to maintain discoverability.

Location: `docs/trunk/ARTIFACTS.md`

### Step 4: Render and verify

Run `uv run ve init` to render the updated templates and verify:
- Templates render without errors
- CLAUDE.md contains the updated signpost pointing to EXTERNAL.md
- docs/trunk/EXTERNAL.md exists with expected content

### Step 5: Run tests

Run `uv run pytest tests/` to verify no regressions were introduced.

## Dependencies

- **progressive_disclosure_refactor**: Must be complete (provides the signpost structure in CLAUDE.md.jinja2)
  - Status: ACTIVE (completed)

## Risks and Open Questions

- **Content scope**: The current external artifacts section in ARTIFACTS.md is relatively brief (~200 words). EXTERNAL.md should be expanded to be a comprehensive reference, but not so large that it defeats the purpose of extraction.
- **Cross-reference consistency**: After this change, external artifacts will be documented in EXTERNAL.md but the ARTIFACTS.md page still discusses artifact types. Ensure the cross-reference is clear.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
