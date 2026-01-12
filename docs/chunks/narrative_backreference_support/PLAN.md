<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds narrative backreference support to source code files, following the
existing pattern established for `# Chunk:` and `# Subsystem:` backreferences. The
implementation extends the backreference parsing infrastructure and adds validation
to ensure referenced narratives exist.

**Key insight from the chunk_reference_decay investigation:** Narratives provide
PURPOSE context (why code exists architecturally), while chunks provide HISTORY
context (what work created the code). This semantic distinction guides how we
document the feature—narrative backreferences are for high-level architectural
understanding, not historical traceability.

**Strategy:**
1. Add a regex-based parser for `# Narrative:` comments (similar to existing patterns)
2. Add validation in `validate_chunk_complete()` to ensure referenced narratives exist
3. Document the format in CLAUDE.md template
4. Write tests following TDD (tests before implementation per TESTING_PHILOSOPHY.md)

**Building on:**
- `src/chunks.py`: Contains `validate_subsystem_refs()` and `validate_investigation_ref()`
  which validate similar artifact references
- `src/narratives.py`: Contains `Narratives` class with `enumerate_narratives()` method
- `src/templates/claude/CLAUDE.md.jinja2`: Documents backreference patterns

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system
  to update CLAUDE.md documentation. Will follow existing template update patterns.

No subsystem deviations discovered.

## Sequence

### Step 1: Write failing tests for narrative backreference validation

Create tests in `tests/test_chunk_validate.py` (or a new test file if more appropriate)
that verify:
1. A chunk with a valid `# Narrative:` backreference in code passes validation
2. A chunk referencing a non-existent narrative produces a validation error
3. The validation extracts the correct narrative path from the backreference format

The test should follow TESTING_PHILOSOPHY.md principles—test meaningful behavior
(validation passes/fails correctly), not trivial assertions.

**Test cases:**
- `test_validate_narrative_ref_valid`: Chunk with `# Narrative: docs/narratives/foo`
  backreference where `docs/narratives/foo/` exists → validation passes
- `test_validate_narrative_ref_missing_narrative`: Chunk with `# Narrative: docs/narratives/bar`
  where narrative doesn't exist → validation error
- `test_validate_narrative_ref_empty_field`: Chunk with no narrative field → validation
  passes (narrative is optional)

Location: `tests/test_chunk_validate.py`

### Step 2: Add validate_narrative_ref() method to Chunks class

Add a new method `validate_narrative_ref(self, chunk_id: str) -> list[str]` to the
`Chunks` class in `src/chunks.py`, following the pattern of `validate_investigation_ref()`:

```python
# Chunk: docs/chunks/narrative_backreference_support - Narrative reference validation
def validate_narrative_ref(self, chunk_id: str) -> list[str]:
    """Validate narrative reference in a chunk's frontmatter.

    Checks:
    1. If narrative field is populated, the referenced narrative
       directory exists in docs/narratives/

    Args:
        chunk_id: The chunk ID to validate.

    Returns:
        List of error messages (empty if valid or no reference).
    """
```

This validates the existing `narrative` field in `ChunkFrontmatter` (already present
in `src/models.py` line 542).

Location: `src/chunks.py`

### Step 3: Integrate narrative validation into validate_chunk_complete()

Call `validate_narrative_ref()` from `validate_chunk_complete()` (around line 795 in
`src/chunks.py`), alongside the existing `validate_investigation_ref()` call.

This ensures narrative references are validated when running `ve chunk validate` and
before chunk completion.

Location: `src/chunks.py#Chunks::validate_chunk_complete`

### Step 4: Run tests and verify Step 1-3 tests pass

Execute `uv run pytest tests/test_chunk_validate.py -v` to confirm the validation
logic works correctly. All previously failing tests from Step 1 should now pass.

### Step 5: Update CLAUDE.md template with narrative backreference documentation

Edit `src/templates/claude/CLAUDE.md.jinja2` to document the `# Narrative:`
backreference format in the "Code Backreferences" section. Add alongside the existing
chunk and subsystem documentation:

```markdown
- `# Narrative: ...` - This code is part of an architectural initiative. Read the
  narrative's OVERVIEW.md for the broader purpose and how this code fits into
  the larger vision.
```

Also add semantic hierarchy clarification:
- **Narratives**: PURPOSE context (why the code exists architecturally)
- **Chunks**: HISTORY context (what work created/modified the code)
- **Subsystems**: PATTERN context (what rules govern the code)

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 6: Regenerate CLAUDE.md and verify changes

Run `uv run ve init` to regenerate CLAUDE.md from the template. Verify the new
documentation appears correctly in the rendered output.

### Step 7: Write test for backreference parsing (if parsing is needed)

**Note:** Based on code review, the existing infrastructure validates frontmatter
fields (like `narrative: foo` in YAML). If we also want to parse `# Narrative:`
comments from source code (not just YAML frontmatter), we need additional parsing.

**Decision point:** The GOAL.md mentions "parser recognizes narrative backreferences...
extract `# Narrative:` comments from source files." This suggests we need source
code comment parsing, not just frontmatter validation.

If source parsing is needed:
1. Add a regex pattern for `# Narrative:` comments in a parsing module
2. Add extraction function similar to how chunk backreferences might be extracted
3. Write tests for the parsing logic

However, reviewing the existing codebase more carefully: the current backreference
comments (`# Chunk:`, `# Subsystem:`) are **documentation conventions** for humans
and agents reading code, not programmatically validated. The validation that exists
is for frontmatter fields.

**Recommendation:** Focus on:
- Frontmatter `narrative` field validation (Steps 1-4) ✓
- Documentation of the `# Narrative:` comment format (Steps 5-6) ✓
- Leave source-code parsing as a future enhancement if programmatic extraction is needed

### Step 8: Final test suite run

Execute `uv run pytest tests/` to ensure all tests pass and no regressions were
introduced.

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments to help future agents trace code
back to the documentation that motivated it:

```python
# Chunk: docs/chunks/narrative_backreference_support - Narrative reference validation
def validate_narrative_ref(self, chunk_id: str) -> list[str]:
    ...
```

## Dependencies

- Chunk `chunk_create_guard` (created_after): Ensures single IMPLEMENTING chunk pattern
- Chunk `orch_attention_reason` (created_after): Orchestrator attention tracking
- Chunk `orch_inject_validate` (created_after): Injection validation patterns
- Chunk `deferred_worktree_creation` (created_after): Worktree creation patterns

These are causal dependencies in the created_after field, not blocking implementation
dependencies.

## Risks and Open Questions

1. **Scope of "parser recognizes"**: The GOAL.md success criterion #1 says "parser
   recognizes narrative backreferences...extract `# Narrative:` comments from source
   files." Current codebase doesn't programmatically extract `# Chunk:` comments either—
   they're documentation conventions. **Resolution:** Focus on frontmatter validation
   and documentation; defer programmatic comment parsing unless explicitly needed.

2. **Validation location**: Should narrative reference validation happen in
   `validate_chunk_complete()` (like investigation refs) or separately?
   **Resolution:** Follow existing pattern—add to `validate_chunk_complete()`.

3. **Cross-project narrative references**: Should we support
   `# Narrative: org/repo::docs/narratives/foo` format?
   **Resolution:** Not in scope for this chunk. Follow existing local-only pattern
   like investigation refs. Cross-project support can be added later if needed.

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

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->