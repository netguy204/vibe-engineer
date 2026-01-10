# Implementation Plan

## Approach

This chunk wires up the `ArtifactIndex.find_tips()` functionality (from chunk 0038) to the artifact creation functions. The approach is:

1. **Modify each creation function** to query `ArtifactIndex.find_tips()` before rendering templates
2. **Update templates** to include `created_after` in the generated frontmatter
3. **Pass tip short names** through the template context to populate the field

The implementation follows the established pattern where:
- Manager classes (`Chunks`, `Narratives`, `Investigations`, `Subsystems`) orchestrate creation
- Templates define the initial frontmatter structure
- `render_to_directory()` injects context variables into templates

Since each artifact type maintains its own independent causal graph (per investigation 0001 findings), chunks reference chunk tips, narratives reference narrative tips, etc.

Testing follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write failing tests for the `created_after` population behavior, then implement the changes.

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the causal ordering feature by populating `created_after` in all workflow artifact types. As the subsystem is in REFACTORING status, we should follow its patterns closely.
- **docs/subsystems/0001-template_system** (status unknown): This chunk USES the template system for rendering. We'll follow the existing `render_to_directory()` pattern.

## Sequence

### Step 1: Write failing tests for chunk creation with `created_after`

Add tests to `tests/test_chunks.py` that verify:
- When creating the first chunk (no existing chunks), `created_after: []` in GOAL.md
- When creating a chunk after one exists, `created_after` contains the previous chunk's short name
- When creating a chunk with multiple tips, all tips are listed in `created_after`

Use `temp_project` fixture and parse the generated GOAL.md frontmatter to verify.

Location: `tests/test_chunks.py`

### Step 2: Update chunk template to include `created_after`

Modify the chunk GOAL.md template to include the `created_after` field in frontmatter. Use Jinja2 syntax to render the list of parent short names.

Location: `src/templates/chunk/GOAL.md.jinja2`

### Step 3: Update `Chunks.create_chunk()` to populate `created_after`

Modify `create_chunk()` to:
1. Import and instantiate `ArtifactIndex`
2. Call `find_tips(ArtifactType.CHUNK)` to get current tip chunks
3. Extract short names from tip directory names (strip the `NNNN-` prefix)
4. Pass the list of short names to `render_to_directory()` as a template variable

Location: `src/chunks.py`

### Step 4: Write failing tests for narrative creation with `created_after`

Add tests to `tests/test_narratives.py` that verify:
- When creating the first narrative (no existing narratives), `created_after: []` in OVERVIEW.md
- When creating a narrative after one exists, `created_after` contains the previous narrative's short name

Location: `tests/test_narratives.py`

### Step 5: Update narrative template to include `created_after`

Modify the narrative OVERVIEW.md template to include the `created_after` field in frontmatter.

Location: `src/templates/narrative/OVERVIEW.md.jinja2`

### Step 6: Update `Narratives.create_narrative()` to populate `created_after`

Modify `create_narrative()` to query `ArtifactIndex.find_tips(ArtifactType.NARRATIVE)` and pass tip short names to the template.

Location: `src/narratives.py`

### Step 7: Write failing tests for investigation creation with `created_after`

Add tests to `tests/test_investigations.py` that verify:
- When creating the first investigation, `created_after: []` in OVERVIEW.md
- When creating an investigation after one exists, `created_after` contains the previous investigation's short name

Location: `tests/test_investigations.py`

### Step 8: Update investigation template to include `created_after`

Modify the investigation OVERVIEW.md template to include the `created_after` field in frontmatter.

Location: `src/templates/investigation/OVERVIEW.md.jinja2`

### Step 9: Update `Investigations.create_investigation()` to populate `created_after`

Modify `create_investigation()` to query `ArtifactIndex.find_tips(ArtifactType.INVESTIGATION)` and pass tip short names to the template.

Location: `src/investigations.py`

### Step 10: Write failing tests for subsystem creation with `created_after`

Add tests to `tests/test_subsystems.py` that verify:
- When creating the first subsystem, `created_after: []` in OVERVIEW.md
- When creating a subsystem after one exists, `created_after` contains the previous subsystem's short name

Location: `tests/test_subsystems.py`

### Step 11: Update subsystem template to include `created_after`

Modify the subsystem OVERVIEW.md template to include the `created_after` field in frontmatter.

Location: `src/templates/subsystem/OVERVIEW.md.jinja2`

### Step 12: Update `Subsystems.create_subsystem()` to populate `created_after`

Modify `create_subsystem()` to query `ArtifactIndex.find_tips(ArtifactType.SUBSYSTEM)` and pass tip short names to the template.

Location: `src/subsystems.py`

### Step 13: Run full test suite and fix any regressions

Ensure all existing tests pass with the new changes. The artifact ordering tests should also exercise the new creation paths.

Location: `tests/`

### Step 14: Update GOAL.md with code_paths

Update `docs/chunks/0039-populate_created_after/GOAL.md` frontmatter with the files modified:
- `src/chunks.py`
- `src/narratives.py`
- `src/investigations.py`
- `src/subsystems.py`
- `src/templates/chunk/GOAL.md.jinja2`
- `src/templates/narrative/OVERVIEW.md.jinja2`
- `src/templates/investigation/OVERVIEW.md.jinja2`
- `src/templates/subsystem/OVERVIEW.md.jinja2`
- `tests/test_chunks.py`
- `tests/test_narratives.py`
- `tests/test_investigations.py`
- `tests/test_subsystems.py`

## Dependencies

- **0037-created_after_field** (ACTIVE): The `created_after` field must exist in all frontmatter models. Verified: `ChunkFrontmatter`, `NarrativeFrontmatter`, `InvestigationFrontmatter`, and `SubsystemFrontmatter` all have `created_after: list[str] = []`.

- **0038-artifact_ordering_index** (ACTIVE): The `ArtifactIndex.find_tips()` method must be available. Verified: `src/artifact_ordering.py` exports `ArtifactIndex` with `find_tips(artifact_type: ArtifactType) -> list[str]`.

## Risks and Open Questions

1. **Short name extraction**: Tips are returned as directory names (e.g., `0037-created_after_field`). We need to extract just the short name portion (`created_after_field`). The pattern is `^\d{4}-(.+)$`. Need to handle edge cases like directories that don't match the pattern.

2. **Index rebuild on creation**: Creating a new artifact changes the tips. The next creation in the same session should see the new artifact as a tip. Verify that `ArtifactIndex` correctly detects the stale cache when a new artifact is created.

3. **Git not present**: `ArtifactIndex` uses git for staleness detection. Per DEC-002, git is not assumed. Need to verify `find_tips()` works (possibly with degraded performance) when not in a git repository.

4. **Empty directory race condition**: If `ArtifactIndex.find_tips()` is called before any artifacts exist, it should return an empty list. The first artifact should get `created_after: []`.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->