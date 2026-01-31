<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements the dependency propagation step of the explicit chunk dependencies narrative. When agents create chunks from a narrative's `proposed_chunks` array, they need index-based `depends_on` references to be automatically translated into chunk directory names.

The implementation has three parts:

1. **Model Extension**: Add `depends_on` field to the `ProposedChunk` Pydantic model in `src/models.py`. This enables parsing of narratives/investigations with `depends_on: [0, 2]` syntax.

2. **Template Guidance**: Update the `/chunk-create` command template to instruct agents on how to detect and resolve dependencies when creating chunks from narratives.

3. **Helper Function** (optional CLI enhancement): Add a helper to resolve index-based dependencies for programmatic use.

The approach follows DEC-005 (commands do not prescribe git operations) - we only guide the agent on how to populate the `depends_on` field, we don't automate commits.

**Key Design Decisions:**
- **Agent-driven resolution**: The chunk-create command template instructs agents on how to resolve dependencies rather than having the CLI do it automatically. This keeps the CLI simple and puts the logic where the context lives.
- **Graceful degradation**: If a dependency's `chunk_directory` is null, warn the user and suggest creating chunks in dependency order.
- **Index-to-name mapping**: The narrative's `proposed_chunks` array provides the mapping - index N maps to `proposed_chunks[N].chunk_directory`.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk USES the workflow artifact lifecycle patterns. No deviations discovered.

## Sequence

### Step 1: Add depends_on field to ProposedChunk model

**File:** `src/models.py`

Add `depends_on: list[int] = []` field to the `ProposedChunk` class. This optional field stores the array of integer indices referencing other prompts in the same `proposed_chunks` array.

```python
class ProposedChunk(BaseModel):
    prompt: str
    chunk_directory: str | None = None
    depends_on: list[int] = []  # Add this field
```

Add a field validator to ensure indices are non-negative:
```python
@field_validator("depends_on")
@classmethod
def validate_depends_on(cls, v: list[int]) -> list[int]:
    for idx in v:
        if idx < 0:
            raise ValueError(f"depends_on indices must be non-negative, got {idx}")
    return v
```

### Step 2: Update chunk-create command template for dependency detection

**File:** `src/templates/commands/chunk-create.md.jinja2`

Add a new step (after step 4 - refining GOAL.md) that instructs the agent to:

1. **Detect narrative context**: Check if the work being created matches a prompt in a narrative's `proposed_chunks` array
2. **Find the matching prompt**: Read the narrative's OVERVIEW.md and find the prompt entry matching this chunk
3. **Resolve dependencies**: If the prompt has `depends_on: [0, 2]`, look up indices 0 and 2 in the same array
4. **Translate to chunk names**: For each index, get the `chunk_directory` value from that entry
5. **Populate depends_on**: Write the resolved chunk directory names to the new chunk's GOAL.md `depends_on` field
6. **Warn on unresolved**: If any referenced entry has `chunk_directory: null`, warn the user that dependencies cannot be resolved and suggest creating chunks in dependency order

Add instructions for the agent to update the narrative's `proposed_chunks[].chunk_directory` with the new chunk's directory name.

### Step 3: Add unit tests for ProposedChunk.depends_on field

**File:** `tests/test_models.py` (create if needed) or add to existing test file

Write tests that verify:
1. `ProposedChunk` accepts valid `depends_on: [0, 1, 2]` (list of non-negative integers)
2. `ProposedChunk` accepts empty `depends_on: []` (the default)
3. `ProposedChunk` rejects negative indices with a clear error message
4. Existing narratives with `depends_on` in frontmatter parse correctly

### Step 4: Add integration test for dependency resolution in narratives

**File:** `tests/test_narratives.py` or new `tests/test_explicit_deps.py`

Write an integration test that:
1. Creates a narrative with `proposed_chunks` including `depends_on` references
2. Parses the narrative frontmatter
3. Verifies that `depends_on` indices are preserved in the parsed model
4. Verifies that looking up `proposed_chunks[index].chunk_directory` returns the expected value

### Step 5: Verify existing tests pass

Run the test suite to ensure no regressions:
```bash
uv run pytest tests/ -v
```

## Dependencies

- **explicit_deps_proposed_schema**: Must be complete (adds template documentation for `depends_on` in narrative/investigation templates)
- The narrative template already documents the `depends_on` field per the prior chunk

## Risks and Open Questions

**Risks:**
- **Stale indices**: If someone reorders the `proposed_chunks` array after adding `depends_on` references, indices become invalid. Mitigation: Document that indices are stable within a planning session; use chunk names once chunks exist.

- **Agent instruction complexity**: The chunk-create template instructions may be complex. Mitigation: Focus on the common case (narrative-derived chunks) and provide clear step-by-step guidance.

**Open Questions (resolved by design):**
- **Why agent-driven vs CLI-driven?** Agent-driven resolution puts logic where context lives. The agent is already reading the narrative to understand the work; adding a few lines to resolve dependencies is simpler than wiring up CLI plumbing.

- **What about investigations?** Same pattern applies - investigations also use `proposed_chunks` with the same schema. The model change covers both.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->