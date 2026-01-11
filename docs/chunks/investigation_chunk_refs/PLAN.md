<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds traceability between investigations and the chunks that emerge from them. The implementation follows the existing patterns established for the `narrative` and `subsystems` fields in chunk frontmatter.

Key patterns to follow:
1. **Schema updates** follow the ChunkFrontmatter model in src/models.py (see lines 531-547)
2. **Validation** follows the pattern in Chunks.validate_subsystem_refs() (src/chunks.py:732-767)
3. **Template updates** follow the existing documentation structure in GOAL.md.jinja2
4. **CLAUDE.md documentation** follows the "Chunk Frontmatter References" section pattern
5. **Workflow integration** follows the /chunk-create command template pattern

Tests follow docs/trunk/TESTING_PHILOSOPHY.md:
- Write failing tests first for validation behavior
- Test meaningful behavior (validation logic), not trivial storage
- Test at boundaries (invalid investigation IDs, non-existent investigations)

## Sequence

### Step 1: Add `investigation` field to ChunkFrontmatter model

Update `src/models.py` to add an optional `investigation` field to the ChunkFrontmatter model.
This mirrors the existing `narrative` field pattern (line 542).

Location: src/models.py#ChunkFrontmatter

Changes:
- Add `investigation: str | None = None` field after the `narrative` field

### Step 2: Update chunk GOAL.md template with `investigation` field

Update the chunk template to include the `investigation` field in both:
1. The frontmatter YAML (add `investigation: null` after `narrative`)
2. The comment block documentation (add INVESTIGATION section after NARRATIVE)

Location: src/templates/chunk/GOAL.md.jinja2

Changes:
- Add `investigation: null` to the frontmatter section (after line 7)
- Add INVESTIGATION documentation to the comment block (after NARRATIVE section, around line 59)

### Step 3: Write failing tests for investigation reference validation

Write tests for the new validation behavior before implementing it:
1. Test that a chunk with a valid investigation reference passes validation
2. Test that a chunk with an invalid investigation reference fails validation
3. Test that a chunk with no investigation reference passes validation

Location: tests/test_chunk_validate.py

Add a new test class `TestInvestigationRefValidation` following the pattern of
`TestSubsystemRefValidation` (lines 498-641).

### Step 4: Implement investigation reference validation

Add a new method `validate_investigation_ref()` to the Chunks class that:
1. Checks if the `investigation` field is populated
2. If populated, verifies the investigation directory exists in `docs/investigations/`
3. Returns list of error messages (empty if valid or no reference)

Update `validate_chunk_complete()` to call this new validation method.

Location: src/chunks.py#Chunks

Changes:
- Add `validate_investigation_ref()` method (follow validate_subsystem_refs pattern)
- Update `validate_chunk_complete()` to include investigation validation

### Step 5: Update CLAUDE.md Chunk Frontmatter References section

Document the `investigation` field in the "Chunk Frontmatter References" section,
explaining its purpose and when implementing agents should read the referenced
investigation.

Location: CLAUDE.md

Changes:
- Add `- **investigation**: References an investigation directory...` bullet point
  to the Chunk Frontmatter References section (after line 37)

### Step 6: Update /chunk-create command template

Update the chunk-create command template to prompt the agent to populate the
`investigation` field when creating a chunk from an investigation's proposed_chunks.

Location: .claude/commands/chunk-create.md

Changes:
- Add guidance after step 5 for populating the investigation field when the chunk
  originates from an investigation

---

**BACKREFERENCE COMMENTS**

Add backreference comments to modified code:
```
# Chunk: docs/chunks/investigation_chunk_refs - Investigation field for traceability
```

## Risks and Open Questions

- **Field name**: Using `investigation` (singular) to match `narrative` (singular) pattern.
  An alternative would be `source_investigation` for clarity, but consistency with
  existing patterns is preferred.

- **Bidirectional linking**: This chunk only implements chunk → investigation linking.
  The inverse (investigation's proposed_chunks.chunk_directory) already exists and
  provides the reverse lookup. No additional work needed for bidirectionality.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->