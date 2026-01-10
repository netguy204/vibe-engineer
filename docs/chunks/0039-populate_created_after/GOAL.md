---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/narratives.py
  - src/investigations.py
  - src/subsystems.py
  - src/templates/chunk/GOAL.md.jinja2
  - src/templates/narrative/OVERVIEW.md.jinja2
  - src/templates/investigation/OVERVIEW.md.jinja2
  - src/templates/subsystem/OVERVIEW.md.jinja2
  - tests/test_chunks.py
  - tests/test_narratives.py
  - tests/test_investigations.py
  - tests/test_subsystems.py
code_references:
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Populate created_after with current chunk tips"
  - ref: src/narratives.py#Narratives::create_narrative
    implements: "Populate created_after with current narrative tips"
  - ref: src/investigations.py#Investigations::create_investigation
    implements: "Populate created_after with current investigation tips"
  - ref: src/subsystems.py#Subsystems::create_subsystem
    implements: "Populate created_after with current subsystem tips"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Template for created_after field in chunk frontmatter"
  - ref: src/templates/narrative/OVERVIEW.md.jinja2
    implements: "Template for created_after field in narrative frontmatter"
  - ref: src/templates/investigation/OVERVIEW.md.jinja2
    implements: "Template for created_after field in investigation frontmatter"
  - ref: src/templates/subsystem/OVERVIEW.md.jinja2
    implements: "Template for created_after field in subsystem frontmatter"
  - ref: tests/test_chunks.py#TestCreatedAfterPopulation
    implements: "Tests for chunk created_after population"
  - ref: tests/test_narratives.py#TestNarrativeCreatedAfterPopulation
    implements: "Tests for narrative created_after population"
  - ref: tests/test_investigations.py#TestInvestigationCreatedAfterPopulation
    implements: "Tests for investigation created_after population"
  - ref: tests/test_subsystems.py#TestSubsystemCreatedAfterPopulation
    implements: "Tests for subsystem created_after population"
narrative: null
subsystems:
  - subsystem_id: "0002-workflow_artifacts"
    relationship: implements
---

# Chunk Goal

## Minor Goal

Populate the `created_after` field automatically when new workflow artifacts are created. This is the third chunk in the causal ordering initiative from `docs/investigations/0001-artifact_sequence_numbering`.

This chunk connects the foundation work:
- `0037-created_after_field` added the `created_after` field to all frontmatter models
- `0038-artifact_ordering_index` implemented `ArtifactIndex` with `find_tips()` functionality

Now we need to use these to set `created_after` when creating new artifacts. Each artifact creation function must:
1. Query `ArtifactIndex.find_tips()` to get current tip artifacts (those with no dependents)
2. Extract the short names from the tips
3. Pass the list of tip short names to the template for frontmatter generation
4. The new artifact's `created_after` will reference these tips, establishing its place in the causal graph

After this chunk, new artifacts will automatically capture their causal relationship to existing work, enabling merge-friendly parallel development.

## Success Criteria

- `create_chunk()` in `src/chunks.py` populates `created_after` with current chunk tips
- `create_narrative()` in `src/narratives.py` populates `created_after` with current narrative tips
- `create_investigation()` in `src/investigations.py` populates `created_after` with current investigation tips
- `create_subsystem()` in `src/subsystems.py` populates `created_after` with current subsystem tips
- Templates for each artifact type include `created_after` in generated frontmatter
- Each artifact type's `created_after` references tips within its own type (chunks reference chunk tips, narratives reference narrative tips, etc.)
- Existing tests pass
- New tests validate `created_after` is populated on artifact creation
- Empty tips list (first artifact of a type) results in `created_after: []`

## Dependencies

This chunk depends on:
- `0037-created_after_field` - The `created_after` field exists in all frontmatter models
- `0038-artifact_ordering_index` - The `ArtifactIndex.find_tips()` method is available