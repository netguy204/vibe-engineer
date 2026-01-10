# Implementation Plan

## Approach

This chunk unifies how proposed chunks are tracked across narratives, subsystems, and investigations by:

1. **Renaming `chunks` to `proposed_chunks`** in narrative templates and existing narratives
2. **Adding `proposed_chunks`** to subsystem templates for consolidation work (keeping existing `chunks` for chunk relationships)
3. **Adding a `ve chunk list-proposed` CLI command** to enumerate proposed-but-not-yet-created chunks across all artifact types
4. **Migrating existing artifacts** to the new field names
5. **Updating documentation** to explain the pattern

The implementation follows existing CLI patterns in `src/ve.py` (click command groups) and leverages the Pydantic models in `src/models.py` for schema validation. Per DEC-001, all functionality is exposed via the CLI. Per DEC-004, file references are relative to project root.

Tests will follow `docs/trunk/TESTING_PHILOSOPHY.md`:
- TDD for the new `list-proposed` command logic
- CLI integration tests using Click's test runner
- Semantic assertions verifying actual output, not just types

## Subsystem Considerations

- **docs/subsystems/0001-template_system** (STABLE): This chunk USES the template system's existing patterns. Templates are updated via direct file edits (not the render_to_directory API), following the `.jinja2` suffix convention.

No deviations discovered. The template system is STABLE, so no opportunistic improvements are needed.

## Sequence

### Step 1: Add `ProposedChunk` Pydantic model

Create a shared model for the `{prompt, chunk_directory}` structure used across all artifact types. This ensures consistent validation.

Location: `src/models.py`

Schema:
```python
class ProposedChunk(BaseModel):
    prompt: str  # The chunk prompt text
    chunk_directory: str | None = None  # Populated when chunk is created
```

Add validation that `prompt` is non-empty.

### Step 2: Update narrative frontmatter schema

Add `NarrativeFrontmatter` Pydantic model with:
- `status`: NarrativeStatus enum (DRAFTING, ACTIVE, COMPLETED)
- `advances_trunk_goal`: str | None
- `proposed_chunks`: list[ProposedChunk] = []

This model will be used by the `list-proposed` command to parse narrative frontmatter.

Location: `src/models.py`

### Step 3: Update subsystem frontmatter schema

Extend `SubsystemFrontmatter` to include `proposed_chunks`:
- `proposed_chunks`: list[ProposedChunk] = []

The existing `chunks` field (list[ChunkRelationship]) remains for tracking already-created chunk relationships.

Location: `src/models.py`

### Step 4: Update narrative template

Rename `chunks` to `proposed_chunks` in the narrative OVERVIEW.md template:

Location: `src/templates/narrative/OVERVIEW.md.jinja2`

Changes:
- Frontmatter: `chunks: []` → `proposed_chunks: []`
- Update schema comment to describe the new field
- Keep existing prose sections (they refer to "chunks" conceptually, not the field name)

### Step 5: Update subsystem template

Add `proposed_chunks` field to subsystem OVERVIEW.md template frontmatter:

Location: `src/templates/subsystem/OVERVIEW.md.jinja2`

Changes:
- Add `proposed_chunks: []` to frontmatter
- Add schema documentation for the field
- Update "Consolidation Chunks" section to reference the frontmatter array

### Step 6: Add `parse_narrative_frontmatter` to narratives module

Add a method to parse and validate narrative OVERVIEW.md frontmatter:

Location: `src/narratives.py`

```python
def parse_narrative_frontmatter(self, narrative_id: str) -> NarrativeFrontmatter | None
```

Follow the pattern from `src/subsystems.py#parse_subsystem_frontmatter`.

### Step 7: Implement `list_proposed_chunks` core logic

Add business logic to collect proposed chunks across all artifact types:

Location: `src/chunks.py` (add new method to Chunks class)

```python
def list_proposed_chunks(self) -> list[dict]:
    """List all proposed chunks across investigations, narratives, and subsystems.

    Returns:
        List of dicts with keys: prompt, chunk_directory, source_type, source_id
        Filtered to entries where chunk_directory is None (not yet created).
    """
```

The method should:
1. Iterate over all investigations, parse frontmatter, extract `proposed_chunks`
2. Iterate over all narratives, parse frontmatter, extract `proposed_chunks`
3. Iterate over all subsystems, parse frontmatter, extract `proposed_chunks`
4. Filter to entries where `chunk_directory` is None or empty
5. Return with source information (which artifact proposed this chunk)

### Step 8: Add `ve chunk list-proposed` CLI command

Location: `src/ve.py`

```python
@chunk.command("list-proposed")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_proposed_chunks(project_dir):
    """List all proposed chunks that haven't been created yet."""
```

Output format:
```
From docs/investigations/0001-memory_leak:
  - Add LRU eviction to ImageCache
From docs/narratives/0003-investigations:
  - Create the investigation OVERVIEW.md template...
```

### Step 9: Migrate existing narrative documents

Update the three existing narratives to use `proposed_chunks`:

Files to update:
- `docs/narratives/0001-cross_repo_chunks/OVERVIEW.md`
- `docs/narratives/0002-subsystem_documentation/OVERVIEW.md`
- `docs/narratives/0003-investigations/OVERVIEW.md`

For each file, rename the frontmatter field `chunks` to `proposed_chunks`.

### Step 10: Migrate existing subsystem documents

Update existing subsystem to add empty `proposed_chunks` if not present:

File: `docs/subsystems/0001-template_system/OVERVIEW.md`

Add `proposed_chunks: []` to frontmatter (no pending consolidation work since it's STABLE).

### Step 11: Update CLAUDE.md documentation

Add a section explaining the `proposed_chunks` pattern:

Location: `CLAUDE.md`

Content:
- Explain that `proposed_chunks` is a cross-cutting field used in narratives, subsystems, and investigations
- Document the `ve chunk list-proposed` command
- Clarify the distinction from subsystem's `chunks` field (which tracks already-created relationships)

### Step 12: Write tests for `list-proposed` command

Location: `tests/test_chunk_list_proposed.py`

Test cases:
1. Empty project returns no output, exit code 0
2. Investigation with proposed chunks shows them
3. Narrative with proposed chunks shows them
4. Subsystem with proposed chunks shows them
5. Already-created chunks (chunk_directory populated) are filtered out
6. Output includes source artifact information
7. Multiple sources are aggregated correctly

### Step 13: Write tests for narrative frontmatter parsing

Location: `tests/test_narratives.py` (extend existing file)

Test cases:
1. Parse valid narrative frontmatter with proposed_chunks
2. Handle missing proposed_chunks field (defaults to empty list)
3. Handle malformed frontmatter gracefully

## Risks and Open Questions

1. **Backward compatibility**: Existing narratives use `chunks`, not `proposed_chunks`. The migration in Steps 9-10 addresses this, but any external tools parsing these files would need updates. This is acceptable since no external tooling exists yet.

2. **Semantic clarity**: The name `proposed_chunks` clearly signals these are proposals, not created chunks. However, for subsystems, we now have both `chunks` (relationships to existing chunks) and `proposed_chunks` (pending consolidation work). The distinction should be documented clearly.

3. **Field naming in investigations**: Investigations already use `proposed_chunks`, so no template change is needed there. The model addition in Step 1 formalizes what already exists.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->