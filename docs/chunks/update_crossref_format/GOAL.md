---
status: SUPERSEDED
ticket: null
parent_chunk: null
code_paths:
- src/**/*.py
- tests/**/*.py
- docs/**/*.md
- src/templates/**/*.jinja2
code_references: []
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["ordering_remove_seqno"]
superseded_by: "scratchpad_remove_infra - Chunk backreferences were eliminated entirely (not just reformatted). Templates now instruct agents to remove all # Chunk: and # Narrative: comments rather than update their format."
---

# Chunk Goal

## Minor Goal

Update all cross-references throughout the codebase from the legacy `NNNN-short_name`
format to the new `short_name` format. This completes the directory naming transition
started in chunk `ordering_remove_seqno`.

This is the right next step because:

1. **Directory naming is already updated** - Chunk `ordering_remove_seqno` renamed all
   artifact directories from `{NNNN}-{short_name}/` to `{short_name}/`. However,
   cross-references in code and frontmatter still use the old format in many places.

2. **Consistency reduces cognitive load** - Mixed formats are confusing. Developers and
   agents should see consistent `short_name` references everywhere.

3. **Investigation 0001 identified this as Phase 4 work** - This is the second half of
   Phase 4 from investigation `artifact_sequence_numbering`. The first half
   (`ordering_remove_seqno`) renamed directories; this chunk updates references.

4. **Cross-type collisions are not an issue** - References remain type-qualified (e.g.,
   `docs/chunks/foo`, `docs/narratives/bar`) so different artifact types can share
   short names safely.

## Success Criteria

1. **Code backreferences updated** - All `# Chunk: docs/chunks/NNNN-name` comments
   in source files are updated to `# Chunk: docs/chunks/name`. Same for
   `# Subsystem:` backreferences.

2. **Frontmatter references updated** - All frontmatter cross-references use short_name:
   - `narrative:` field in chunk frontmatter
   - `subsystems[].subsystem_id` in chunk frontmatter
   - `parent_chunk` in chunk frontmatter
   - `chunks[].chunk_id` in subsystem frontmatter
   - Any other cross-artifact references

3. **Subsystem code_references updated** - The `ref:` paths in subsystem frontmatter
   don't change (they reference code, not artifacts), but any artifact directory
   references are updated.

4. **Migration tool created** - An automated migration script in the chunk directory
   that can update cross-references. This helps future projects using the legacy format.

5. **No broken references** - `ve chunk validate` and `ve subsystem validate` (if they
   exist) pass, or manual verification confirms all references resolve.

6. **Tests pass** - All existing tests pass after updates.